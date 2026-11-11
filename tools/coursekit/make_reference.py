"""Создание reference.docx со стилями методички."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


def _set_font(style, name: str, size: float) -> None:
    style.font.name = name
    style.font.size = Pt(size)
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        fonts.set(qn(attr), name)


def _shade(style, fill: str) -> None:
    rpr = style.element.get_or_add_rPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    rpr.append(shading)


def _page_number(section) -> None:
    paragraph = section.footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instruction, end):
        run._r.append(node)


def build_reference_docx(out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    document = Document()

    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)

    styles = document.styles
    normal = styles["Normal"]
    _set_font(normal, "Times New Roman", 14)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.first_line_indent = Cm(1.25)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    body = styles["Body Text"]
    _set_font(body, "Times New Roman", 14)
    body.paragraph_format.line_spacing = 1.5
    body.paragraph_format.first_line_indent = Cm(1.25)
    body.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    heading1 = styles["Heading 1"]
    _set_font(heading1, "Times New Roman", 18)
    heading1.font.bold = True
    heading1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    heading1.paragraph_format.first_line_indent = Cm(0)
    heading1.paragraph_format.space_after = Pt(12)

    heading2 = styles["Heading 2"]
    _set_font(heading2, "Times New Roman", 16)
    heading2.font.bold = True
    heading2.paragraph_format.first_line_indent = Cm(0)

    heading3 = styles["Heading 3"]
    _set_font(heading3, "Times New Roman", 14)
    heading3.font.bold = True
    heading3.font.italic = True
    heading3.paragraph_format.first_line_indent = Cm(0)

    code = styles.add_style("Source Code", 1)
    _set_font(code, "Consolas", 10)
    code.paragraph_format.line_spacing = 1.0
    code.paragraph_format.first_line_indent = Cm(0)
    code.paragraph_format.space_after = Pt(0)
    _shade(code, "F2F2F2")

    for name in ("Title", "Subtitle", "Author"):
        try:
            style = styles[name]
        except KeyError:
            style = styles.add_style(name, 1)
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        style.paragraph_format.first_line_indent = Cm(0)

    _page_number(section)

    document.save(out)
    return out
