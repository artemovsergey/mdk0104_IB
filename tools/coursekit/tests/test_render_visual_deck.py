import shutil
from pathlib import Path

import pytest

from coursekit.config import CourseConfig
from coursekit.render_deck import Slide
from coursekit.render_visual_deck import (
    build_visual_deck,
    choose_layout,
    extract_chips,
    extract_image_alts,
    inline,
)


def test_extract_chips_removes_comment():
    text, chips = extract_chips("A\n<!-- chips: один, два -->\nB")
    assert chips == ["один", "два"]
    assert "chips" not in text


def test_extract_image_alts_skips_code_fences():
    text = "![схема](a.png)\n```bash\n![не картинка](fence.png)\n```\n"
    assert extract_image_alts(text) == [("схема", "a.png")]


def test_choose_layout_by_signals():
    title = Slide(title="Неделя 2. Тема")
    assert choose_layout(title, 0) == "title"
    assert choose_layout(Slide(title="План лекции", bullets=["а"] * 6), 1) == "plan"
    assert choose_layout(Slide(title="Схема", image="x.png"), 2) == "image"
    assert choose_layout(Slide(title="Код", code=["a"], bullets=["b", "c"]), 3) == "split-code"
    assert choose_layout(Slide(title="Код", code=["a"], bullets=["b"]), 4) == "code-full"
    assert choose_layout(Slide(title="Резюме: итог", bullets=["а"] * 6), 5) == "summary"
    assert choose_layout(Slide(title="Вопросы", bullets=["а"] * 6), 6) == "questions"
    assert choose_layout(Slide(title="Карточки", bullets=["а"] * 5), 7) == "cards"
    assert choose_layout(Slide(title="Тезис", bullets=["а", "б"]), 8) == "statement"


def test_inline_escapes_and_marks_up():
    assert inline("<script>**важно** `cmd`</script>") == (
        "&lt;script&gt;<strong>важно</strong> <span class=\"inl-code\">cmd</span>&lt;/script&gt;"
    )


@pytest.mark.skipif(
    shutil.which("google-chrome") is None or shutil.which("pdftoppm") is None,
    reason="нужны google-chrome и pdftoppm",
)
@pytest.mark.integration
def test_build_visual_deck_smoke(tmp_path: Path):
    cfg = CourseConfig(
        code="Тест", title="Тестовый курс", specialty="", group="", year="2026",
        teacher="Учитель", repo_slug="test",
    )
    markdown = (
        "# Тест. Неделя 1. Тема\n\nПодзаголовок курса\n\n"
        "<!-- notes: заметка титула -->\n\n---\n\n"
        "## План\n\n- Пункт раз\n- Пункт два\n\n<!-- notes: заметка плана -->\n\n---\n\n"
        "## Тезис\n\n- **Жирный** вывод про `код`\n- Пояснение\n\n<!-- notes: заметка тезиса -->\n"
    )
    out = tmp_path / "out" / "test-w01-lecture-visual.pptx"
    warnings = build_visual_deck(markdown, cfg, out, base_dir=tmp_path, work_dir=tmp_path / "work")
    assert out.exists()
    assert not any("PDF" in w or "PNG" in w for w in warnings)
    pdf = out.with_suffix(".pdf")
    assert pdf.exists()

    from pptx import Presentation

    prs = Presentation(out)
    assert len(prs.slides) == 3
    notes = [s.notes_slide.notes_text_frame.text for s in prs.slides]
    assert "заметка плана" in notes[1]
    html_text = (tmp_path / "work" / "deck.html").read_text(encoding="utf-8")
    assert "<script>" not in html_text
    assert "<strong>Жирный</strong>" in html_text
