from pathlib import Path

import pytest
from pptx import Presentation

from coursekit.config import load_config
from coursekit.model import parse_document
from coursekit.render_pptx import build_pptx

MD = """# Лекция 1. Основы

## План лекции
1. Введение
2. Типы данных

## 1. Введение
Первый тезис.
- Второй тезис.
- Третий тезис.

## Резюме
Итог.

## Контрольные вопросы
1. Что такое CLR?
"""


@pytest.mark.integration
def test_pptx_structure(tmp_path: Path):
    doc = parse_document(MD, Path("Лекция 1.md"))
    out = build_pptx(doc, load_config(Path("course.yml")), tmp_path / "l1.pptx")
    prs = Presentation(out)
    texts = [" ".join(sh.text for sh in s.shapes if sh.has_text_frame) for s in prs.slides]
    assert any("План лекции" in t for t in texts)
    assert any("Резюме" in t for t in texts)
    assert any("Что такое CLR" in t for t in texts)


@pytest.mark.integration
def test_pptx_shapes_fit_slide(tmp_path: Path):
    doc = parse_document(MD, Path("Лекция 1.md"))
    out = build_pptx(doc, load_config(Path("course.yml")), tmp_path / "l1.pptx")
    prs = Presentation(out)
    width, height = prs.slide_width, prs.slide_height
    for slide in prs.slides:
        for shape in slide.shapes:
            assert shape.left >= 0 and shape.top >= 0
            assert shape.left + shape.width <= width + 10
            assert shape.top + shape.height <= height + 10


@pytest.mark.integration
def test_pptx_has_speaker_notes(tmp_path: Path):
    doc = parse_document(MD, Path("Лекция 1.md"))
    out = build_pptx(doc, load_config(Path("course.yml")), tmp_path / "l1.pptx")
    prs = Presentation(out)
    assert any(slide.notes_slide.notes_text_frame.text.strip() for slide in prs.slides)
