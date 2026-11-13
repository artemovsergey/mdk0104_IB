from dataclasses import replace
from pathlib import Path

from coursekit.plan import load_plan, validate_plan

FIXTURE = Path(__file__).parent / "fixtures" / "plan" / "plan.yml"


def _codes(issues):
    return [i.code for i in issues]


def test_valid_plan_has_no_errors():
    plan = load_plan(FIXTURE)
    assert [i for i in validate_plan(plan, FIXTURE.parent) if i.level == "E"] == []


def test_hours_sum_mismatch_is_error():
    plan = load_plan(FIXTURE)
    broken = replace(plan, hours={**plan.hours, "theory": 2})
    assert "E-HOURS-KIND" in _codes(validate_plan(broken, FIXTURE.parent))


def test_total_hours_mismatch_is_error():
    plan = load_plan(FIXTURE)
    broken = replace(plan, hours={**plan.hours, "total": 99})
    assert "E-HOURS-TOTAL" in _codes(validate_plan(broken, FIXTURE.parent))


def test_duplicate_id_is_error():
    plan = load_plan(FIXTURE)
    section = plan.sections[0]
    lessons = (section.lessons[0], replace(section.lessons[1], id="1-1"))
    broken = replace(plan, sections=(replace(section, lessons=lessons),))
    assert "E-DUP-ID" in _codes(validate_plan(broken, FIXTURE.parent))


def test_unknown_prerequisite_is_error():
    plan = load_plan(FIXTURE)
    section = plan.sections[0]
    lessons = (section.lessons[0], replace(section.lessons[1], prerequisites=("9-9",)))
    broken = replace(plan, sections=(replace(section, lessons=lessons),))
    assert "E-PREREQ-MISSING" in _codes(validate_plan(broken, FIXTURE.parent))


def test_prerequisite_from_later_lesson_is_error():
    plan = load_plan(FIXTURE)
    section = plan.sections[0]
    lessons = (replace(section.lessons[0], prerequisites=("1-2",)), section.lessons[1])
    broken = replace(plan, sections=(replace(section, lessons=lessons),))
    assert "E-PREREQ-ORDER" in _codes(validate_plan(broken, FIXTURE.parent))


def test_unknown_kind_is_error():
    plan = load_plan(FIXTURE)
    section = plan.sections[0]
    lessons = (replace(section.lessons[0], kind="семинар"), section.lessons[1])
    broken = replace(plan, sections=(replace(section, lessons=lessons),))
    assert "E-KIND" in _codes(validate_plan(broken, FIXTURE.parent))


def test_missing_file_is_error(tmp_path):
    plan = load_plan(FIXTURE)
    broken = replace(plan, sections=(replace(plan.sections[0], lessons=(
        replace(plan.sections[0].lessons[0], file="course/нет.md"), plan.sections[0].lessons[1])),))
    assert "E-FILE-MISSING" in _codes(validate_plan(broken, FIXTURE.parent))


def test_planned_true_does_not_require_file(tmp_path):
    plan = load_plan(FIXTURE)
    section = plan.sections[0]
    lessons = (replace(section.lessons[0], file=None, planned=True), section.lessons[1])
    assert "E-FILE-MISSING" not in _codes(validate_plan(replace(plan, sections=(replace(section, lessons=lessons),)), FIXTURE.parent))


def test_planned_true_with_existing_file_warns():
    plan = load_plan(FIXTURE)
    section = plan.sections[0]
    lessons = (replace(section.lessons[0], planned=True), section.lessons[1])
    assert "W-PLANNED-EXISTS" in _codes(validate_plan(replace(plan, sections=(replace(section, lessons=lessons),)), FIXTURE.parent))


def test_lesson_without_sources_warns():
    plan = load_plan(FIXTURE)
    section = plan.sections[0]
    lessons = (replace(section.lessons[0], sources=()), section.lessons[1])
    assert "W-SOURCES" in _codes(validate_plan(replace(plan, sections=(replace(section, lessons=lessons),)), FIXTURE.parent))


def test_section_without_practice_warns():
    plan = load_plan(FIXTURE)
    section = replace(plan.sections[0], lessons=(plan.sections[0].lessons[0],))
    assert "W-SECTION-NO-PRACTICE" in _codes(validate_plan(replace(plan, sections=(section,)), FIXTURE.parent))


def test_unknown_outcome_warns():
    plan = load_plan(FIXTURE)
    section = plan.sections[0]
    lessons = (replace(section.lessons[0], outcomes=("ПК 9.9",)), section.lessons[1])
    assert "W-OUTCOME-UNKNOWN" in _codes(validate_plan(replace(plan, sections=(replace(section, lessons=lessons),)), FIXTURE.parent))


def test_unlisted_course_file_warns():
    plan = load_plan(FIXTURE)
    orphan = FIXTURE.parent / "course" / "Раздел 1. Основы" / "Лекция 2. Лишняя.md"
    orphan.write_text("# Лишняя\n", encoding="utf-8")
    try:
        assert "W-ORPHAN" in _codes(validate_plan(plan, FIXTURE.parent))
    finally:
        orphan.unlink()
