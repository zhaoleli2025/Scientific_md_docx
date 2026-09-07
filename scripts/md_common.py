#!/usr/bin/env python3
"""Shared Markdown parsing helpers for the scientific-md-docx skill."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence
from urllib.parse import unquote


HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")
IMAGE_RE = re.compile(r"^\s*!\[(?P<alt>[^]]*)\]\((?P<target>[^)]+)\)\s*$")
REFERENCE_HEADING_RE = re.compile(
    r"^\s*#{1,6}\s+(?:references|bibliography)\s*$", re.IGNORECASE
)
REFERENCE_ENTRY_RE = re.compile(
    r"^(?P<indent>\s*)(?P<number>\d+)[.)](?P<space>\s+)(?P<text>\S.*)$"
)
FENCE_RE = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
CITATION_EXPRESSION = r"\d+(?:\s*(?:,|[-–—])\s*\d+)*"
CITATION_RE = re.compile(
    rf"(?<![\w!])\[(?P<cites>{CITATION_EXPRESSION})\](?!\s*\()"
)
SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
TABLE_CAPTION_RE = re.compile(
    r"Table\s+(?:[A-Za-z]*\d+|[IVXLCDM]+)[.:]\s+\S.*", re.IGNORECASE
)
BACKTICK_RUN_RE = re.compile(r"`+")
INLINE_MATH_RE = re.compile(r"\$[^$\n]+\$")
INLINE_LINK_RE = re.compile(r"!?\[[^]\n]*\]\([^)\n]+\)")
AUTOLINK_RE = re.compile(r"<(?:https?://|mailto:)[^>\n]+>", re.IGNORECASE)


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


def fence_closer(fence: str) -> re.Pattern[str]:
    return re.compile(rf"^\s*{re.escape(fence[0])}{{{len(fence)},}}\s*$")


def fence_mask(lines: Sequence[str]) -> list[bool]:
    """Mask fenced blocks and block comments, raising on an unclosed fence."""

    mask = [False] * len(lines)
    close_re: re.Pattern[str] | None = None
    opening_line = 0
    in_comment = False
    for index, line in enumerate(lines):
        if in_comment:
            mask[index] = True
            if "-->" in line:
                in_comment = False
            continue

        if close_re is None:
            stripped = line.lstrip()
            if stripped.startswith("<!--"):
                mask[index] = True
                in_comment = "-->" not in stripped[4:]
                continue
            match = FENCE_RE.match(line)
            if match is None:
                continue
            fence = match.group("fence")
            close_re = fence_closer(fence)
            opening_line = index + 1
            mask[index] = True
            continue

        mask[index] = True
        if close_re.match(line):
            close_re = None

    if close_re is not None:
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


def reference_section_end(
    lines: Sequence[str], heading: int, mask: Sequence[bool] | None = None
) -> int:
    """Return the first heading after the bibliography, or the document end."""

    active_mask = list(mask) if mask is not None else fence_mask(lines)
    for index in range(heading + 1, len(lines)):
        if not active_mask[index] and HEADING_RE.match(lines[index]):
            return index
    return len(lines)


def parse_references(
    lines: Sequence[str], mask: Sequence[bool] | None = None
) -> tuple[int | None, list[ReferenceEntry]]:
    """Parse numbered entries under the final References heading."""

    active_mask = list(mask) if mask is not None else fence_mask(lines)
    heading = reference_heading_index(lines, active_mask)
    if heading is None:
        return None, []

    section_end = reference_section_end(lines, heading, active_mask)
    starts: list[int] = []
    for index in range(heading + 1, section_end):
        if not active_mask[index] and REFERENCE_ENTRY_RE.match(lines[index]):
            starts.append(index)

    entries: list[ReferenceEntry] = []
    seen: set[int] = set()
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else section_end
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


def _code_span_ranges(line: str) -> list[tuple[int, int]]:
    """Return ranges for matched CommonMark-style backtick code spans."""

    runs = list(BACKTICK_RUN_RE.finditer(line))
    ranges: list[tuple[int, int]] = []
    opener_index = 0
    while opener_index < len(runs):
        opener = runs[opener_index]
        closer_index = opener_index + 1
        while closer_index < len(runs):
            closer = runs[closer_index]
            if len(closer.group(0)) == len(opener.group(0)):
                ranges.append((opener.start(), closer.end()))
                opener_index = closer_index + 1
                break
            closer_index += 1
        else:
            opener_index += 1
    return ranges


def _protected_inline_ranges(line: str) -> list[tuple[int, int]]:
    """Return inline ranges whose bracketed numbers are literal content."""

    ranges = _code_span_ranges(line)
    for pattern in (INLINE_MATH_RE, INLINE_LINK_RE, AUTOLINK_RE):
        ranges.extend((match.start(), match.end()) for match in pattern.finditer(line))
    return ranges


def _is_escaped(line: str, index: int) -> bool:
    backslashes = 0
    index -= 1
    while index >= 0 and line[index] == "\\":
        backslashes += 1
        index -= 1
    return backslashes % 2 == 1


def iter_line_citations(line: str, line_index: int = 0) -> Iterator[CitationOccurrence]:
    """Yield citations in one line, excluding literal inline constructs."""

    protected = _protected_inline_ranges(line)
    for match in CITATION_RE.finditer(line):
        if _is_escaped(line, match.start()) or any(
            start <= match.start() < end for start, end in protected
        ):
            continue
        yield CitationOccurrence(
            line=line_index,
            start=match.start(),
            end=match.end(),
            raw=match.group(0),
            numbers=tuple(expand_citation(match.group("cites"))),
        )


def iter_citations(
    lines: Sequence[str],
    mask: Sequence[bool] | None = None,
    *,
    exclude_references: bool = True,
) -> Iterator[CitationOccurrence]:
    """Yield citations outside fenced blocks and the bibliography section."""

    active_mask = list(mask) if mask is not None else fence_mask(lines)
    heading = reference_heading_index(lines, active_mask) if exclude_references else None
    section_end = (
        reference_section_end(lines, heading, active_mask)
        if heading is not None
        else None
    )
    for line_index in range(len(lines)):
        if active_mask[line_index] or (
            heading is not None and heading <= line_index < section_end
        ):
            continue
        yield from iter_line_citations(lines[line_index], line_index)


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
    code_ranges = _code_span_ranges(value)
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value) and value[index + 1] == "|":
            buffer.append("|")
            index += 2
            continue
        in_code = any(start <= index < end for start, end in code_ranges)
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


def is_table_start(
    lines: Sequence[str], index: int, mask: Sequence[bool] | None = None
) -> bool:
    return (
        index + 1 < len(lines)
        and (mask is None or (not mask[index] and not mask[index + 1]))
        and "|" in lines[index]
        and is_table_separator(lines[index + 1])
    )


def parse_table_rows(
    lines: Sequence[str], start: int, mask: Sequence[bool] | None = None
) -> tuple[int, list[tuple[int, list[str]]]]:
    rows: list[tuple[int, list[str]]] = []
    index = start
    while index < len(lines) and lines[index].strip() and "|" in lines[index]:
        if mask is not None and mask[index]:
            break
        rows.append((index, split_table_row(lines[index])))
        index += 1
    return index, rows


def plain_text(markdown: str) -> str:
    """Return a rough visible-text form for sizing and metadata."""

    value = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", markdown)
    value = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\*\*(.+?)\*\*", r"\1", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = value.replace(r"\|", "|")
    return value.strip()


def parse_link_target(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        return value[1 : value.index(">")]
    match = re.match(r"(\S+)(?:\s+[\"'].*[\"'])?$", value)
    return match.group(1) if match else value


def parse_image_target(raw: str) -> str:
    """Parse and URL-decode a local or remote Markdown image target."""

    return unquote(parse_link_target(raw))


def table_caption_text(line: str) -> str | None:
    """Return a `Table N. ...` caption, allowing optional emphasis wrappers."""

    value = line.strip()
    for marker in ("**", "__", "*", "_"):
        if value.startswith(marker) and value.endswith(marker):
            value = value[len(marker) : -len(marker)].strip()
            break
    return value if TABLE_CAPTION_RE.fullmatch(value) else None


def next_nonblank_index(lines: Sequence[str], start: int) -> int | None:
    for index in range(start, len(lines)):
        if lines[index].strip():
            return index
    return None


def document_title(lines: Sequence[str], fallback: str) -> str:
    for line in lines:
        match = HEADING_RE.match(line)
        if match and len(match.group(1)) == 1:
            return plain_text(match.group(2))
    return fallback


def strip_front_matter(lines: Sequence[str]) -> tuple[list[str], int]:
    """Remove initial YAML front matter and return the source line offset."""

    if not lines or lines[0].strip() != "---":
        return list(lines), 0
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return list(lines[index + 1 :]), index + 1
    raise ValueError("Unclosed YAML front matter")
