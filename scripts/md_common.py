#!/usr/bin/env python3
"""Shared Markdown parsing helpers for the scientific-md-docx skill."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence


REFERENCE_HEADING_RE = re.compile(
    r"^\s*#{1,6}\s+(?:references|bibliography)\s*$", re.IGNORECASE
)
REFERENCE_ENTRY_RE = re.compile(r"^(?P<indent>\s*)(?P<number>\d+)[.)](?P<space>\s+)(?P<text>\S.*)$")
FENCE_RE = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
CITATION_RE = re.compile(
    r"(?<![\w!])\[(?P<cites>\d+(?:\s*(?:,|[-–—])\s*\d+)*)\](?!\s*\()"
)
SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")


@dataclass(frozen=True)
class ReferenceEntry:
    """One numbered bibliography entry and its source line range."""

    number: int
    start: int
    end: int
    lines: tuple[str, ...]

    def with_number(self, number: int) -> list[str]:
        match = REFERENCE_ENTRY_RE.match(self.lines[0])
        if match is None:
            raise ValueError(f"Malformed reference entry at line {self.start + 1}")
        first = (
            f"{match.group('indent')}{number}.{match.group('space')}"
            f"{match.group('text')}"
        )
        return [first, *self.lines[1:]]


@dataclass(frozen=True)
class CitationOccurrence:
    """A numeric Markdown citation outside a fenced block."""

    line: int
    start: int
    end: int
    raw: str
    numbers: tuple[int, ...]


def fence_mask(lines: Sequence[str]) -> list[bool]:
    """Return a mask for fenced lines, raising on an unclosed fence."""

    mask = [False] * len(lines)
    active_char: str | None = None
    active_length = 0
    opening_line = 0
    for index, line in enumerate(lines):
        if active_char is None:
            match = FENCE_RE.match(line)
            if match is None:
                continue
            fence = match.group("fence")
            active_char = fence[0]
            active_length = len(fence)
            opening_line = index + 1
            mask[index] = True
            continue

        mask[index] = True
        close_re = re.compile(
            rf"^\s*{re.escape(active_char)}{{{active_length},}}\s*$"
        )
        if close_re.match(line):
            active_char = None
            active_length = 0

    if active_char is not None:
        raise ValueError(f"Unclosed fenced block beginning at line {opening_line}")
    return mask


def reference_heading_index(
    lines: Sequence[str], mask: Sequence[bool] | None = None
) -> int | None:
    """Find a References/Bibliography heading outside fenced content."""

    active_mask = list(mask) if mask is not None else fence_mask(lines)
    for index, line in enumerate(lines):
        if not active_mask[index] and REFERENCE_HEADING_RE.match(line):
            return index
    return None


def parse_references(
    lines: Sequence[str], mask: Sequence[bool] | None = None
) -> tuple[int | None, list[ReferenceEntry]]:
    """Parse numbered entries under the final References heading."""

    active_mask = list(mask) if mask is not None else fence_mask(lines)
    heading = reference_heading_index(lines, active_mask)
    if heading is None:
        return None, []

    starts: list[int] = []
    for index in range(heading + 1, len(lines)):
        if not active_mask[index] and REFERENCE_ENTRY_RE.match(lines[index]):
            starts.append(index)

    entries: list[ReferenceEntry] = []
    seen: set[int] = set()
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        while end > start + 1 and not lines[end - 1].strip():
            end -= 1
        match = REFERENCE_ENTRY_RE.match(lines[start])
        if match is None:
            continue
        number = int(match.group("number"))
        if number in seen:
            raise ValueError(
                f"Duplicate reference number {number} at line {start + 1}"
            )
        seen.add(number)
        entries.append(
            ReferenceEntry(number, start, end, tuple(lines[start:end]))
        )
    return heading, entries


def expand_citation(expression: str) -> list[int]:
    """Expand a citation body such as '1, 3-5' into unique numbers."""

    numbers: list[int] = []
    for part in re.split(r"\s*,\s*", expression.strip()):
        if not part:
            continue
        range_match = re.fullmatch(r"(\d+)\s*[-–—]\s*(\d+)", part)
        if range_match:
            first, last = map(int, range_match.groups())
            if last < first:
                raise ValueError(f"Descending citation range {part!r}")
            numbers.extend(range(first, last + 1))
        elif part.isdigit():
            numbers.append(int(part))
        else:
            raise ValueError(f"Malformed citation expression {expression!r}")

    ordered: list[int] = []
    seen: set[int] = set()
    for number in numbers:
        if number not in seen:
            seen.add(number)
            ordered.append(number)
    return ordered


def compress_numbers(numbers: Iterable[int]) -> str:
    """Format sorted unique numbers, compressing runs of three or more."""

    values = sorted(set(numbers))
    parts: list[str] = []
    start = 0
    while start < len(values):
        end = start
        while end + 1 < len(values) and values[end + 1] == values[end] + 1:
            end += 1
        run_length = end - start + 1
        if run_length >= 3:
            parts.append(f"{values[start]}–{values[end]}")
        elif run_length == 2:
            parts.extend((str(values[start]), str(values[end])))
        else:
            parts.append(str(values[start]))
        start = end + 1
    return ",".join(parts)


def format_citation(numbers: Iterable[int]) -> str:
    return f"[{compress_numbers(numbers)}]"


def iter_citations(
    lines: Sequence[str],
    mask: Sequence[bool] | None = None,
    *,
    stop_at_references: bool = True,
) -> Iterator[CitationOccurrence]:
    """Yield numeric citations outside code fences and the bibliography."""

    active_mask = list(mask) if mask is not None else fence_mask(lines)
    heading = reference_heading_index(lines, active_mask) if stop_at_references else None
    limit = heading if heading is not None else len(lines)
    for line_index in range(limit):
        if active_mask[line_index]:
            continue
        for match in CITATION_RE.finditer(lines[line_index]):
            yield CitationOccurrence(
                line=line_index,
                start=match.start(),
                end=match.end(),
                raw=match.group(0),
                numbers=tuple(expand_citation(match.group("cites"))),
            )


def citation_order(
    lines: Sequence[str], entries: Sequence[ReferenceEntry], mask: Sequence[bool]
) -> tuple[list[int], set[int]]:
    """Return first-use reference order and the set actually cited."""

    available = {entry.number for entry in entries}
    order: list[int] = []
    cited: set[int] = set()
    for occurrence in iter_citations(lines, mask):
        for number in occurrence.numbers:
            if number not in available:
                raise ValueError(
                    f"Citation {number} at line {occurrence.line + 1} "
                    "has no bibliography entry"
                )
            cited.add(number)
            if number not in order:
                order.append(number)
    for entry in entries:
        if entry.number not in order:
            order.append(entry.number)
    return order, cited


def split_table_row(line: str) -> list[str]:
    """Split a pipe-table row while preserving escaped pipes and code spans."""

    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|") and not value.endswith(r"\|"):
        value = value[:-1]

    cells: list[str] = []
    buffer: list[str] = []
    in_code = False
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value) and value[index + 1] == "|":
            buffer.append("|")
            index += 2
            continue
        if char == "`":
            in_code = not in_code
            buffer.append(char)
            index += 1
            continue
        if char == "|" and not in_code:
            cells.append("".join(buffer).strip())
            buffer.clear()
        else:
            buffer.append(char)
        index += 1
    cells.append("".join(buffer).strip())
    return cells


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(SEPARATOR_CELL_RE.fullmatch(cell) for cell in cells)


def plain_text(markdown: str) -> str:
    """Return a rough visible-text form for sizing and metadata."""

    value = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", markdown)
    value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\*\*(.+?)\*\*", r"\1", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = value.replace(r"\|", "|")
    return value.strip()


def strip_front_matter(lines: Sequence[str]) -> tuple[list[str], int]:
    """Remove initial YAML front matter and return the source line offset."""

    if not lines or lines[0].strip() != "---":
        return list(lines), 0
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return list(lines[index + 1 :]), index + 1
    raise ValueError("Unclosed YAML front matter")
