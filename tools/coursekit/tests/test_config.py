from pathlib import Path

from coursekit.config import load_config, slugify


def test_load_config_reads_course_fields(tmp_path: Path):
    p = tmp_path / "course.yml"
    p.write_text(
        'course:\n  code: "МДК 01.04"\n  title: "Системное программирование"\n'
        '  specialty: "09.02.07, ИБ"\n  group: "ИБ-243"\n  year: "2026/2027"\n'
        '  teacher: "Иванов И. И."\n  repo_slug: "mdk0104-ib"\n'
        "build:\n  docx: true\n  pdf: false\n  pptx: true\n  figures: true\n  book: false\n",
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.code == "МДК 01.04"
    assert cfg.teacher == "Иванов И. И."
    assert cfg.pdf is False


def test_slugify_transliterates_cyrillic():
    assert slugify("Лекция 1. Основы C# и .NET") == "lekciya-1-osnovy-c-i-net"
    assert (
        slugify("Раздел 3. Многопоточность и асинхронность")
        == "razdel-3-mnogopotochnost-i-asinhronnost"
    )
