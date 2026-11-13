from pathlib import Path

from coursekit.plan import dump_plan, load_plan, scaffold
from coursekit.plan_import import import_plan


def _tree(tmp_path: Path) -> Path:
    base = tmp_path / "course" / "Раздел 1. Основы"
    base.mkdir(parents=True)
    (base / "Лекция 1. Введение.md").write_text("# Введение\n", encoding="utf-8")
    (base / "Практическая работа 1. Первая программа.md").write_text("# Первая\n", encoding="utf-8")
    return tmp_path


def test_import_reads_sections_and_kinds(tmp_path):
    plan = import_plan(_tree(tmp_path))
    assert [s.number for s in plan.sections] == [1]
    kinds = [l.kind for l in plan.sections[0].lessons]
    assert kinds == ["lecture", "practice"]
    assert plan.sections[0].lessons[0].title == "Введение"


def test_import_takes_hours_from_ktp(tmp_path):
    ktp = {"sections": [{"number": 1, "title": "Основы", "lessons": [
        {"kind": "lecture", "number": 1, "title": "Введение", "hours": 4},
        {"kind": "practice", "number": 1, "title": "Первая программа", "hours": 2},
    ]}]}
    plan = import_plan(_tree(tmp_path), ktp)
    assert plan.sections[0].lessons[0].hours == 4
    assert plan.sections[0].lessons[1].hours == 2


def test_scaffold_creates_missing_files(tmp_path):
    root = _tree(tmp_path)
    plan = import_plan(root)
    created = scaffold(plan, root)
    assert created == []
    from dataclasses import replace
    broken = replace(plan, sections=(replace(plan.sections[0], lessons=(
        replace(plan.sections[0].lessons[0], planned=True, file="course/Раздел 1. Основы/Лекция 2. Новая.md"),)),))
    created = scaffold(broken, root)
    assert len(created) == 1 and created[0].exists()


def test_dump_plan_roundtrip(tmp_path):
    root = _tree(tmp_path)
    plan = import_plan(root)
    out = tmp_path / "plan.yml"
    dump_plan(plan, out)
    assert load_plan(out).sections[0].lessons[0].title == "Введение"
