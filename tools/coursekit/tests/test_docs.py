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
