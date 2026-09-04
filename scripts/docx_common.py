#!/usr/bin/env python3
"""Small Word-formatting primitives shared by the DOCX renderer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from docx.text.run import Run

from md_common import plain_text


BLACK = RGBColor(0, 0, 0)
BLUE = RGBColor(5, 99, 193)
GRAY = RGBColor(80, 80, 80)
EMU_PER_INCH = 914400


@dataclass(frozen=True)
class Profile:
    font: str
    font_size: float
    citation_style: str
    table_style: str
    margin: float
    line_spacing: float
    title_size: float


PROFILES = {
    "scientific": Profile(
        "Times New Roman", 11.0, "brackets", "three-line", 0.78, 1.12, 16.0
    ),
    "nature": Profile(
        "Times New Roman", 12.0, "superscript", "three-line", 0.68, 1.08, 16.0
    ),
    "clinical": Profile("Arial", 10.5, "brackets", "grid", 0.65, 1.08, 15.0),
    "supervisor": Profile("Aptos", 11.0, "brackets", "three-line", 0.72, 1.08, 17.0),
}


def set_run_font(
    run: Run,
    font: str,
    size: float,
    *,
    bold: bool | None = None,
    italic: bool | None = None,
    color: RGBColor = BLACK,
    underline: bool | None = None,
) -> None:
    run.font.name = font
    run.font.size = Pt(size)
    run.font.color.rgb = color
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if underline is not None:
        run.underline = underline
    properties = run._element.get_or_add_rPr()
    fonts = properties.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        properties.insert(0, fonts)
    for attribute in ("ascii", "hAnsi", "eastAsia", "cs"):
        fonts.set(qn(f"w:{attribute}"), font)


def shade_paragraph(paragraph, fill: str) -> None:
    properties = paragraph._p.get_or_add_pPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:fill"), fill)


def paragraph_left_border(paragraph, color: str = "B7B7B7") -> None:
    properties = paragraph._p.get_or_add_pPr()
    borders = properties.find(qn("w:pBdr"))
    if borders is None:
        borders = OxmlElement("w:pBdr")
        properties.append(borders)
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "12")
    left.set(qn("w:space"), "8")
    left.set(qn("w:color"), color)
    borders.append(left)


def horizontal_rule(paragraph) -> None:
    properties = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "777777")
    borders.append(bottom)
    properties.append(borders)


def set_cell_margins(
    cell, top: int = 65, start: int = 85, bottom: int = 65, end: int = 85
) -> None:
    properties = cell._tc.get_or_add_tcPr()
    margins = properties.find(qn("w:tcMar"))
    if margins is None:
        margins = OxmlElement("w:tcMar")
        properties.append(margins)
    for name, value in (
        ("top", top),
        ("start", start),
        ("bottom", bottom),
        ("end", end),
    ):
        node = margins.find(qn(f"w:{name}"))
        if node is None:
            node = OxmlElement(f"w:{name}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_cell_width(cell, width_inches: float) -> None:
    cell.width = Inches(width_inches)
    properties = cell._tc.get_or_add_tcPr()
    width = properties.find(qn("w:tcW"))
    if width is None:
        width = OxmlElement("w:tcW")
        properties.append(width)
    width.set(qn("w:w"), str(int(width_inches * 1440)))
    width.set(qn("w:type"), "dxa")


def repeat_table_header(row) -> None:
    properties = row._tr.get_or_add_trPr()
    if properties.find(qn("w:tblHeader")) is None:
        properties.append(OxmlElement("w:tblHeader"))


def prevent_row_split(row) -> None:
    properties = row._tr.get_or_add_trPr()
    if properties.find(qn("w:cantSplit")) is None:
        properties.append(OxmlElement("w:cantSplit"))


def set_three_line_borders(table) -> None:
    properties = table._tbl.tblPr
    borders = properties.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        properties.append(borders)
    for edge, value, size in (
        ("top", "single", "12"),
        ("bottom", "single", "12"),
        ("left", "nil", "0"),
        ("right", "nil", "0"),
        ("insideH", "nil", "0"),
        ("insideV", "nil", "0"),
    ):
        existing = borders.find(qn(f"w:{edge}"))
        if existing is not None:
            borders.remove(existing)
        node = OxmlElement(f"w:{edge}")
        node.set(qn("w:val"), value)
        node.set(qn("w:sz"), size)
        node.set(qn("w:color"), "000000")
        borders.append(node)


def set_header_bottom_border(cell) -> None:
    properties = cell._tc.get_or_add_tcPr()
    borders = properties.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        properties.append(borders)
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:color"), "000000")
    borders.append(bottom)


def clear_document_body(document) -> None:
    """Remove template body content while retaining styles and section data."""

    body = document._element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    for kind, text in (("begin", None), (None, " PAGE "), ("end", None)):
        if kind:
            node = OxmlElement("w:fldChar")
            node.set(qn("w:fldCharType"), kind)
        else:
            node = OxmlElement("w:instrText")
            node.set(
                "{http://www.w3.org/XML/1998/namespace}space", "preserve"
            )
            node.text = text
        run._r.append(node)


def parse_link_target(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        return value[1 : value.index(">")]
    match = re.match(r"(\S+)(?:\s+[\"'].*[\"'])?$", value)
    return match.group(1) if match else value


def linearize_math(value: str) -> str:
    replacements = {
        r"\leq": "≤",
        r"\le": "≤",
        r"\geq": "≥",
        r"\ge": "≥",
        r"\neq": "≠",
        r"\pm": "±",
        r"\times": "×",
        r"\cdot": "·",
        r"\sum": "∑",
        r"\sqrt": "√",
        r"\infty": "∞",
        r"\alpha": "α",
        r"\beta": "β",
        r"\gamma": "γ",
        r"\delta": "δ",
        r"\epsilon": "ε",
        r"\mu": "μ",
        r"\sigma": "σ",
        r"\tau": "τ",
        r"\ldots": "…",
    }
    result = value.strip()
    result = re.sub(
        r"\\bar\{([^{}]+)\}",
        lambda match: match.group(1) + "\u0304",
        result,
    )
    fraction = re.compile(r"\\frac\{([^{}]+)\}\{([^{}]+)\}")
    while fraction.search(result):
        result = fraction.sub(r"(\1)/(\2)", result)
    for source, target in replacements.items():
        result = result.replace(source, target)
    result = re.sub(
        r"\\(?:mathrm|text|operatorname)\{([^{}]+)\}", r"\1", result
    )
    return result.replace("{", "").replace("}", "")


def configure_document(
    document, profile: Profile, *, landscape: bool, page_numbers: bool
) -> None:
    section = document.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    if landscape:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = (
            section.page_height,
            section.page_width,
        )
    for side in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(section, side, Inches(profile.margin))
    section.header_distance = Inches(0.3)
    section.footer_distance = Inches(0.3)

    normal = document.styles["Normal"]
    normal.font.name = profile.font
    normal.font.size = Pt(profile.font_size)
    normal.font.color.rgb = BLACK
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = profile.line_spacing

    heading_sizes = {
        "Title": profile.title_size,
        "Heading 1": max(profile.font_size + 3.0, 14.0),
        "Heading 2": max(profile.font_size + 2.0, 13.0),
        "Heading 3": max(profile.font_size + 1.0, 12.0),
        "Heading 4": profile.font_size,
        "Heading 5": profile.font_size,
        "Heading 6": profile.font_size,
    }
    for name, size in heading_sizes.items():
        style = document.styles[name]
        style.font.name = profile.font
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = BLACK
        style.paragraph_format.space_before = Pt(8)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.keep_with_next = True
        properties = style._element.get_or_add_pPr()
        inherited_border = properties.find(qn("w:pBdr"))
        if inherited_border is not None:
            properties.remove(inherited_border)

    try:
        caption = document.styles["Caption"]
    except KeyError:
        caption = document.styles.add_style("Caption", WD_STYLE_TYPE.PARAGRAPH)
    caption.font.name = profile.font
    caption.font.size = Pt(max(8.5, profile.font_size - 1.0))
    caption.font.italic = True
    if page_numbers:
        add_page_number(section.footer.paragraphs[0])


def heading_size(profile: Profile, level: int, is_title: bool) -> float:
    if is_title:
        return profile.title_size
    return {
        1: max(profile.font_size + 3.0, 14.0),
        2: max(profile.font_size + 2.0, 13.0),
        3: max(profile.font_size + 1.0, 12.0),
    }.get(level, profile.font_size)


def document_title(lines: Sequence[str], fallback: str) -> str:
    for line in lines:
        match = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if match:
            return plain_text(match.group(1))
    return fallback
