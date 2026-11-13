from dataclasses import replace
from pathlib import Path

from coursekit.plan import compare_with_ktp, load_ktp, load_plan

DIR = Path(__file__).parent / "fixtures" / "plan"


def test_same_plan_and_ktp_have_no_diff():
    assert compare_with_ktp(load_plan(DIR / "plan.yml"), load_ktp(DIR / "ktp.yml")) == []


def test_changed_hours_produce_diff():
    plan = load_plan(DIR / "plan.yml")
    section = plan.sections[0]
    lessons = (replace(section.lessons[0], hours=6), section.lessons[1])
    issues = compare_with_ktp(replace(plan, sections=(replace(section, lessons=lessons),)), load_ktp(DIR / "ktp.yml"))
    assert "D-HOURS" in [i.code for i in issues]


def test_extra_lesson_produces_added():
    plan = load_plan(DIR / "plan.yml")
    ktp = load_ktp(DIR / "ktp.yml")
    ktp["sections"][0]["lessons"] = ktp["sections"][0]["lessons"][:1]
    issues = compare_with_ktp(plan, ktp)
    assert "D-ADDED" in [i.code for i in issues]


def test_reordered_topics_produce_moved():
    plan = load_plan(DIR / "plan.yml")
    ktp = load_ktp(DIR / "ktp.yml")
    ktp["sections"][0]["lessons"].reverse()
    issues = compare_with_ktp(plan, ktp)
    assert "D-MOVED" in [i.code for i in issues]
