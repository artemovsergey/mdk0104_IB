from pathlib import Path

from coursekit.model import (
    canonical_title,
    detect_kind,
    missing_required,
    parse_document,
)


def test_detect_kind_from_filename():
    assert detect_kind(Path("course/Раздел 1/Лекция 1. Основы.md")) == "lecture"
    assert detect_kind(Path("course/Раздел 1/Практическая работа 2. Поток.md")) == "practice"
    assert (
        detect_kind(Path("course/Раздел 1/Самостоятельная работа 1. Калькулятор.md"))
        == "selfstudy"
    )
    assert detect_kind(Path("course/examen.md")) == "exam"


def test_alias_maps_to_canonical():
    assert canonical_title("Краткая справочная информация") == "Теоретическая часть"
    assert canonical_title("Цель работы:") == "Цель работы"
    assert canonical_title("15 Вариантов заданий") == "Варианты заданий"
    assert canonical_title("Неизвестный раздел") is None


def test_parse_lecture_sections():
    md = (
        "# Лекция 1. Основы\n\n## План лекции\n1. Введение\n\n"
        "## 1. Введение\nТекст\n\n## Резюме\nИтог\n"
    )
    doc = parse_document(md, Path("Лекция 1.md"))
    assert doc.kind == "lecture"
    assert [s.title for s in doc.sections] == ["План лекции", "1. Введение", "Резюме"]


def test_missing_required_section_reported():
    md = "# Практическая работа 2. Поток\n\n## Краткая справочная информация\nТекст\n"
    doc = parse_document(md, Path("Практическая работа 2.md"))
    assert "Цель работы" in missing_required(doc)
    assert "Ход работы" in missing_required(doc)
