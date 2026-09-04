#!/usr/bin/env python3
"""Renumber relative numeric Markdown citations by first appearance."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from md_common import (
    CITATION_RE,
    citation_order,
    expand_citation,
    fence_mask,
    format_citation,
    parse_references,
)


def normalize(text: str) -> tuple[str, list[int]]:
    """Return normalized Markdown and old numbers that remain uncited."""

    trailing_newline = text.endswith("\n")
    lines = text.splitlines()
    mask = fence_mask(lines)
    heading, entries = parse_references(lines, mask)

    citations_exist = any(
        CITATION_RE.search(line)
        for index, line in enumerate(lines)
        if not mask[index] and (heading is None or index < heading)
    )
    if citations_exist and heading is None:
        raise ValueError("Numeric citations are present but no References heading exists")
    if citations_exist and not entries:
        raise ValueError("Numeric citations are present but no numbered references exist")
    if heading is None:
        return text, []
    if not entries:
        if any(line.strip() for line in lines[heading + 1 :]):
            raise ValueError("References section has content but no numbered entries")
        return text, []
    if any(line.strip() for line in lines[heading + 1 : entries[0].start]):
        raise ValueError("Unexpected text before the first numbered reference")

    order, cited = citation_order(lines, entries, mask)
    mapping = {old: new for new, old in enumerate(order, start=1)}

    body = list(lines[:heading])
    body_mask = mask[:heading]
    for index, line in enumerate(body):
        if body_mask[index]:
            continue

        def replace(match):
            old_numbers = expand_citation(match.group("cites"))
            return format_citation(mapping[number] for number in old_numbers)

        body[index] = CITATION_RE.sub(replace, line)

    by_number = {entry.number: entry for entry in entries}
    normalized_lines = [*body, lines[heading]]
    if entries:
        normalized_lines.append("")
        for new_number, old_number in enumerate(order, start=1):
            normalized_lines.extend(by_number[old_number].with_number(new_number))

    result = "\n".join(normalized_lines).rstrip()
    if trailing_newline:
        result += "\n"
    uncited = [entry.number for entry in entries if entry.number not in cited]
    return result, uncited


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        if path.exists():
            os.chmod(temporary, path.stat().st_mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Markdown document")
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("--in-place", action="store_true")
    destination.add_argument("--output", type=Path)
    destination.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if citations or references are not canonical",
    )
    return parser.parse_args()


def main() -> int:
    args = arguments()
    try:
        original = args.input.read_text(encoding="utf-8")
        normalized, uncited = normalize(original)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if uncited:
        values = ", ".join(map(str, uncited))
        print(
            f"warning: bibliography entries not cited in the body: {values}",
            file=sys.stderr,
        )

    changed = normalized != original
    if args.check:
        if changed:
            print("citation order or formatting is not canonical", file=sys.stderr)
            return 1
        print("citations and bibliography numbering are canonical")
        return 0

    if args.in_place:
        if changed:
            atomic_write(args.input, normalized)
        print(f"standardized {args.input} ({'changed' if changed else 'unchanged'})")
    elif args.output:
        if args.output.exists():
            print(f"error: output already exists: {args.output}", file=sys.stderr)
            return 2
        atomic_write(args.output, normalized)
        print(f"created {args.output}")
    else:
        sys.stdout.write(normalized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
