#!/usr/bin/env python3
"""Validate scientific Markdown structure before DOCX rendering."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from md_common import (
    CITATION_RE,
    citation_order,
    fence_mask,
    format_citation,
    is_table_separator,
    iter_citations,
    parse_references,
    split_table_row,
    strip_front_matter,
)


HEADING_RE = re.compile(r"^\s*(#{1,6})\s+(.+?)\s*$")
IMAGE_RE = re.compile(r"^\s*!\[([^]]*)\]\(([^)]+)\)\s*$")
DOI_RE = re.compile(r"(?:doi:\s*|https?://doi\.org/)(10\.\d{4,9}/\S+)", re.I)


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    line: int | None
    message: str


def add(
    issues: list[Issue], severity: str, code: str, message: str, line: int | None = None
) -> None:
    issues.append(Issue(severity, code, line, message))


def validate(path: Path) -> list[Issue]:
    issues: list[Issue] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return [Issue("error", "read", None, str(error))]

    original_lines = text.splitlines()
    try:
        body_lines, offset = strip_front_matter(original_lines)
    except ValueError as error:
        add(issues, "error", "front-matter", str(error), 1)
        return issues

    try:
        mask = fence_mask(body_lines)
    except ValueError as error:
        add(issues, "error", "fence", str(error), None)
        return issues

    headings = [
        (index, match)
        for index, line in enumerate(body_lines)
        if not mask[index] and (match := HEADING_RE.match(line))
    ]
    titles = [(index, match) for index, match in headings if len(match.group(1)) == 1]
    if not titles:
        add(issues, "warning", "title", "No level-1 document title is present")
    elif len(titles) > 1:
        add(
            issues,
            "warning",
            "title",
            "More than one level-1 title is present",
            titles[1][0] + offset + 1,
        )

    for index, match in headings:
        if CITATION_RE.search(match.group(2)):
            add(
                issues,
                "warning",
                "heading-citation",
                "Move numeric citations from the heading to supporting prose",
                index + offset + 1,
            )

    try:
        heading, entries = parse_references(body_lines, mask)
    except ValueError as error:
        add(issues, "error", "references", str(error))
        return issues

    citations = list(iter_citations(body_lines, mask))
    if citations and heading is None:
        add(
            issues,
            "error",
            "references-missing",
            "Numeric citations are present but no References heading exists",
        )
    elif citations and not entries:
        add(
            issues,
            "error",
            "references-empty",
            "Numeric citations are present but the bibliography has no numbered entries",
            (heading + offset + 1) if heading is not None else None,
        )

    if heading is not None:
        first_entry = entries[0].start if entries else len(body_lines)
        for index in range(heading + 1, first_entry):
            if body_lines[index].strip():
                add(
                    issues,
                    "error",
                    "reference-preamble",
                    "Unexpected text before the first numbered reference",
                    index + offset + 1,
                )
        later_headings = [
            index
            for index, _match in headings
            if index > heading
        ]
        if later_headings:
            add(
                issues,
                "warning",
                "references-not-final",
                "The References section should be the final document section",
                later_headings[0] + offset + 1,
            )

    if entries:
        available = {entry.number for entry in entries}
        for occurrence in citations:
            for number in occurrence.numbers:
                if number not in available:
                    add(
                        issues,
                        "error",
                        "citation-missing-reference",
                        f"Citation {number} has no bibliography entry",
                        occurrence.line + offset + 1,
                    )

        if not any(issue.severity == "error" for issue in issues):
            order, cited = citation_order(body_lines, entries, mask)
            expected_order = list(range(1, len(entries) + 1))
            if order != expected_order:
                add(
                    issues,
                    "warning",
                    "citation-order",
                    "References are not numbered by first citation; run standardize_citations.py",
                )
            for occurrence in citations:
                expected = format_citation(occurrence.numbers)
                if occurrence.raw != expected:
                    add(
                        issues,
                        "warning",
                        "citation-format",
                        f"Use canonical citation form {expected} instead of {occurrence.raw}",
                        occurrence.line + offset + 1,
                    )
            uncited = [entry.number for entry in entries if entry.number not in cited]
            if uncited:
                add(
                    issues,
                    "warning",
                    "uncited-reference",
                    "Bibliography entries are not cited: " + ", ".join(map(str, uncited)),
                )

        numbers = [entry.number for entry in entries]
        if numbers != list(range(1, len(numbers) + 1)):
            add(
                issues,
                "warning",
                "reference-numbering",
                "Bibliography entries must be contiguous and ordered from 1",
            )

        seen_dois: dict[str, int] = {}
        for entry in entries:
            joined = " ".join(entry.lines)
            match = DOI_RE.search(joined)
            if not match:
                continue
            doi = match.group(1).rstrip(".,;)").lower()
            if doi in seen_dois:
                add(
                    issues,
                    "warning",
                    "duplicate-doi",
                    f"Reference duplicates DOI from entry {seen_dois[doi]}",
                    entry.start + offset + 1,
                )
            else:
                seen_dois[doi] = entry.number

    index = 0
    while index + 1 < len(body_lines):
        if mask[index]:
            index += 1
            continue
        candidate = body_lines[index]
        separator = body_lines[index + 1]
        if "|" in candidate and not mask[index + 1] and is_table_separator(separator):
            columns = len(split_table_row(candidate))
            separator_columns = len(split_table_row(separator))
            if columns != separator_columns:
                add(
                    issues,
                    "error",
                    "table-columns",
                    f"Header has {columns} cells but separator has {separator_columns}",
                    index + offset + 2,
                )
            cursor = index + 2
            rows = 0
            while (
                cursor < len(body_lines)
                and "|" in body_lines[cursor]
                and body_lines[cursor].strip()
            ):
                if mask[cursor]:
                    break
                row_columns = len(split_table_row(body_lines[cursor]))
                if row_columns != columns:
                    add(
                        issues,
                        "error",
                        "table-columns",
                        f"Table row has {row_columns} cells; expected {columns}",
                        cursor + offset + 1,
                    )
                rows += 1
                cursor += 1
            if rows == 0:
                add(
                    issues,
                    "warning",
                    "empty-table",
                    "Table has a header but no data rows",
                    index + offset + 1,
                )
            index = cursor
            continue
        index += 1

    for index, line in enumerate(body_lines):
        if mask[index]:
            continue
        image = IMAGE_RE.match(line)
        if image:
            target = image.group(2).strip().split(maxsplit=1)[0].strip("<>")
            if re.match(r"https?://", target, re.I):
                add(
                    issues,
                    "warning",
                    "remote-image",
                    "The DOCX renderer does not download remote images",
                    index + offset + 1,
                )
            else:
                image_path = (path.parent / target).resolve()
                if not image_path.is_file():
                    add(
                        issues,
                        "error",
                        "image-missing",
                        f"Local image does not exist: {target}",
                        index + offset + 1,
                    )
        if re.search(r"^\s*\[\^[^]]+\]:", line) or re.search(r"\[\^[^]]+\]", line):
            add(
                issues,
                "warning",
                "footnote",
                "Markdown footnotes are not supported by the bundled DOCX renderer",
                index + offset + 1,
            )
        if re.match(r"^\s*</?[A-Za-z][^>]*>\s*$", line):
            add(
                issues,
                "warning",
                "html",
                "Raw block HTML may not render as intended",
                index + offset + 1,
            )

    return issues


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument(
        "--strict", action="store_true", help="Treat warnings as validation failure"
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    issues = validate(args.input)
    if args.as_json:
        print(json.dumps([asdict(issue) for issue in issues], indent=2))
    elif issues:
        for issue in issues:
            location = f":{issue.line}" if issue.line is not None else ""
            print(
                f"{args.input}{location}: {issue.severity}: "
                f"{issue.code}: {issue.message}"
            )
    else:
        print(f"validated {args.input}: no structural issues")

    errors = any(issue.severity == "error" for issue in issues)
    warnings = any(issue.severity == "warning" for issue in issues)
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
