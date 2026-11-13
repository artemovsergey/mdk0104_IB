from pathlib import Path

from coursekit.model import Document
from coursekit.render_docs import build_docs_md


def test_docs_include_titlepage_contents_and_sources(tmp_path):
    docs = []
    text = build_docs_md(
        [],
        cfg=None,
        sources=[{"id": "a", "title": "Док", "url": "https://e.com"}],
        titlepage_text="# Титул\nМДК 01.04\n",
    )
    assert text.startswith("# Титул")
    assert "Содержание" in text
    assert "https://e.com" in text


def test_docs_without_titlepage_warns():
    text = build_docs_md([], cfg=None, sources=[], titlepage_text=None)
    assert "WARN" in text or "черновик" in text.lower()


def test_toc_does_not_repeat_lecture_number():
    docs = [
        Document(path=Path("course/Раздел 1. Основы/Лекция 1. Типы.md"), kind="lecture", number=1, title="Лекция 1. Типы данных")
    ]
    text = build_docs_md(docs, cfg=None, sources=[], titlepage_text="# Титул")
    assert "- Лекция 1. Типы данных" in text
    assert "Лекция 1. Лекция 1." not in text


def test_order_by_plan_uses_plan_sequence():
    from coursekit.plan import Lesson, Plan, Section
    from coursekit.render_docs import order_by_plan

    docs = [
        Document(path=Path("course/Раздел 1. Основы/Практическая работа 1. Типы.md"), kind="practice", number=1, title="Практическая работа 1. Типы"),
        Document(path=Path("course/Раздел 1. Основы/Лекция 1. Типы.md"), kind="lecture", number=1, title="Лекция 1. Типы"),
    ]
    plan = Plan(
        schema=1,
        course={"code": "МДК 01.04"},
        hours={},
        outcomes=[],
        sections=[
            Section(
                number=1,
                title="Основы",
                goal="",
                lessons=[
                    Lesson(id="1-p1", kind="practice", number=1, title="Типы", hours=2,
                           file="course/Раздел 1. Основы/Практическая работа 1. Типы.md"),
                    Lesson(id="1-l1", kind="lecture", number=1, title="Типы", hours=2,
                           file="course/Раздел 1. Основы/Лекция 1. Типы.md"),
                ],
            )
        ],
    )
    ordered = order_by_plan(docs, plan)
    assert [doc.kind for doc in ordered] == ["practice", "lecture"]


def test_docs_can_omit_titlepage_for_pdf():
    text = build_docs_md([], cfg=None, sources=[], titlepage_text="# Титул", titlepage=False)
    assert not text.startswith("# Титул")
    assert "черновик" not in text.lower()


def test_build_pdf_without_toc(tmp_path):
    from coursekit.config import CourseConfig
    from coursekit.render_pdf import build_pdf

    doc = Document(path=tmp_path / "doc.md", kind="meta", number=0, title="Методичка")
    doc.raw = "# Раздел 1\n\nТекст.\n"
    cfg = CourseConfig(code="МДК 01.04", title="Тест", specialty="09.02.07", group="ИБ-1", year="2026/2027", teacher="Преподаватель", repo_slug="t")
    out = build_pdf(doc, cfg, tmp_path / "doc.pdf", tmp_path / "work", toc=False)
    assert out.exists() and out.stat().st_size > 0


def test_toc_sections_are_headings():
    from coursekit.render_docs import build_docs_md

    docs = [
        Document(path=Path("course/Раздел 1. Основы/Лекция 1. Типы.md"), kind="lecture", number=1, title="Лекция 1. Типы"),
        Document(path=Path("course/Раздел 2. ООП/Лекция 2. Классы.md"), kind="lecture", number=2, title="Лекция 2. Классы"),
    ]
    text = build_docs_md(docs, cfg=None, sources=[], titlepage_text="# Титул")
    assert "\n\n### Раздел 1. Основы\n" in text
    assert "\n\n### Раздел 2. ООП\n" in text
    assert "**Раздел 1." not in text


def test_build_pdf_cover_has_subtitle(tmp_path):
    import subprocess

    from coursekit.config import CourseConfig
    from coursekit.render_pdf import build_pdf

    doc = Document(path=tmp_path / "doc.md", kind="meta", number=0, title="Методические указания")
    doc.raw = "# Раздел 1\n\nТекст.\n"
    cfg = CourseConfig(code="МДК 01.04", title="Системное программирование", specialty="09.02.07", group="ИБ-1", year="2026/2027", teacher="Преподаватель", repo_slug="t")
    out = build_pdf(doc, cfg, tmp_path / "doc.pdf", tmp_path / "work", toc=False, subtitle=cfg.title)
    text = subprocess.run(["pdftotext", str(out), "-"], capture_output=True, text=True).stdout
    assert "Методические указания" in text
    assert "Системное программирование" in text


def test_toc_escapes_hash_in_section_name():
    from coursekit.render_docs import build_docs_md

    docs = [
        Document(path=Path("course/Раздел 1. Основы .NET и С#/Лекция 1. Типы.md"), kind="lecture", number=1, title="Лекция 1. Типы"),
    ]
    text = build_docs_md(docs, cfg=None, sources=[], titlepage_text="# Титул")
    assert "### Раздел 1. Основы .NET и С\\#" in text
