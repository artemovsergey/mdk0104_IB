from pathlib import Path

import pytest

from coursekit.plan import PlanError, load_plan

FIXTURE = Path(__file__).parent / "fixtures" / "plan" / "plan.yml"


def test_load_plan_reads_sections_and_lessons():
    plan = load_plan(FIXTURE)
    assert plan.schema == 1
    assert plan.course["code"] == "МДК 01.04"
    assert len(plan.sections) == 1
    assert [l.id for l in plan.sections[0].lessons] == ["1-1", "1-2"]
    assert plan.sections[0].lessons[1].prerequisites == ("1-1",)
    assert plan.sections[0].lessons[0].planned is False


def test_load_plan_rejects_unknown_schema(tmp_path):
    bad = tmp_path / "plan.yml"
    bad.write_text("schema: 99\n", encoding="utf-8")
    with pytest.raises(PlanError, match="schema"):
        load_plan(bad)


def test_load_plan_rejects_non_mapping(tmp_path):
    bad = tmp_path / "plan.yml"
    bad.write_text("- просто список\n", encoding="utf-8")
    with pytest.raises(PlanError):
        load_plan(bad)
