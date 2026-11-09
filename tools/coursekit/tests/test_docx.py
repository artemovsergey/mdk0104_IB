from pathlib import Path

import pytest
from docx import Document as Docx

from coursekit.config import load_config
from coursekit.make_reference import build_reference_docx
from coursekit.model import parse_document
from coursekit.render_docx import build_docx


@pytest.mark.integration
def test_docx_has_gost_like_page_setup(tmp_path: Path):
    ref = build_reference_docx(tmp_path / "reference.docx")
    assert ref.exists()
    md = "# Лекция 1. Основы\n\n## План лекции\n1. Введение\n\n## 1. Введение\nТекст с кириллицей.\n"
    doc = parse_document(md, Path("Лекция 1.md"))
    out = build_docx(doc, load_config(Path("course.yml")), tmp_path / "l1.docx", tmp_path)
    d = Docx(out)
    s = d.sections[0]
    assert round(s.left_margin.cm, 1) == 3.0
    assert round(s.right_margin.cm, 1) == 1.5
    assert d.styles["Normal"].font.name == "Times New Roman"
    assert d.styles["Normal"].font.size.pt == 14


@pytest.mark.integration
def test_missing_image_becomes_placeholder(tmp_path: Path):
    md = "# Лекция 1\n\n![Схема работы](images/none.png)\n"
    doc = parse_document(md, Path("Лекция 1.md"))
    out = build_docx(doc, load_config(Path("course.yml")), tmp_path / "l1.docx", tmp_path)
    text = "\n".join(p.text for p in Docx(out).paragraphs)
    assert "Скриншот отсутствует" in text
