"""Модель и загрузка рабочего плана курса (plan.yml)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PLAN_SCHEMA = 1


class PlanError(Exception):
    """Ошибка чтения или формата plan.yml."""


@dataclass(frozen=True)
class Lesson:
    id: str
    kind: str
    number: int
    title: str
    hours: int
    prerequisites: tuple[str, ...] = ()
    outcomes: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    file: str | None = None
    slides: str | None = None
    planned: bool = False


@dataclass(frozen=True)
class Section:
    number: int
    title: str
    goal: str
    lessons: tuple[Lesson, ...]


@dataclass(frozen=True)
class Plan:
    schema: int
    course: dict[str, str]
    hours: dict[str, int]
    outcomes: tuple[dict[str, str], ...]
    sections: tuple[Section, ...]

    @property
    def lessons(self) -> tuple[Lesson, ...]:
        return tuple(lesson for section in self.sections for lesson in section.lessons)


@dataclass(frozen=True)
class Issue:
    level: str
    code: str
    message: str
    lesson_id: str | None = None


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(item) for item in value)


def _lesson(raw: dict[str, Any]) -> Lesson:
    return Lesson(
        id=str(raw["id"]),
        kind=str(raw["kind"]),
        number=int(raw["number"]),
        title=str(raw["title"]),
        hours=int(raw.get("hours", 0)),
        prerequisites=_as_tuple(raw.get("prerequisites")),
        outcomes=_as_tuple(raw.get("outcomes")),
        sources=_as_tuple(raw.get("sources")),
        file=str(raw["file"]) if raw.get("file") else None,
        slides=str(raw["slides"]) if raw.get("slides") else None,
        planned=bool(raw.get("planned", False)),
    )


def _section(raw: dict[str, Any]) -> Section:
    return Section(
        number=int(raw["number"]),
        title=str(raw["title"]),
        goal=str(raw.get("goal", "")),
        lessons=tuple(_lesson(item) for item in raw.get("lessons") or ()),
    )


LESSON_KINDS = (
    "lecture",
    "practice",
    "selfstudy",
    "coursedesign",
    "consultation",
    "exam",
)

_HOUR_KIND = {
    "theory": "lecture",
    "practice": "practice",
    "course_design": "coursedesign",
    "selfstudy": "selfstudy",
}


def _hours_issues(plan: Plan) -> list[Issue]:
    issues: list[Issue] = []
    actual: dict[str, int] = {kind: 0 for kind in LESSON_KINDS}
    for lesson in plan.lessons:
        if lesson.kind in actual:
            actual[lesson.kind] += lesson.hours
    for key, kind in _HOUR_KIND.items():
        expected = int(plan.hours.get(key, 0))
        if actual[kind] != expected:
            issues.append(
                Issue(
                    level="E",
                    code="E-HOURS-KIND",
                    message=(
                        f"часы «{key}» в шапке: {expected}, "
                        f"а по занятиям вида «{kind}»: {actual[kind]}"
                    ),
                )
            )
    total = (
        int(plan.hours.get("theory", 0))
        + int(plan.hours.get("practice", 0))
        + int(plan.hours.get("course_design", 0))
        + int(plan.hours.get("selfstudy", 0))
    )
    declared = int(plan.hours.get("total", 0))
    if declared != total:
        issues.append(
            Issue(
                level="E",
                code="E-HOURS-TOTAL",
                message=f"total в шапке: {declared}, а сумма разделов: {total}",
            )
        )
    return issues


def _order_issues(plan: Plan) -> list[Issue]:
    issues: list[Issue] = []
    seen_ids: set[str] = set()
    seen_numbers: set[tuple[str, int]] = set()
    position: dict[str, int] = {}
    indexed = list(enumerate(plan.lessons))
    for index, lesson in indexed:
        position.setdefault(lesson.id, index)
        if lesson.id in seen_ids:
            issues.append(
                Issue("E", "E-DUP-ID", f"идентификатор «{lesson.id}» повторяется", lesson.id)
            )
        seen_ids.add(lesson.id)
        key = (lesson.kind, lesson.number)
        if key in seen_numbers:
            issues.append(
                Issue(
                    "E",
                    "E-DUP-NUMBER",
                    f"номер {lesson.number} у вида «{lesson.kind}» повторяется",
                    lesson.id,
                )
            )
        seen_numbers.add(key)
        if lesson.kind not in LESSON_KINDS:
            issues.append(
                Issue(
                    "E",
                    "E-KIND",
                    f"неизвестный вид занятия «{lesson.kind}»",
                    lesson.id,
                )
            )
    for index, lesson in indexed:
        for prerequisite in lesson.prerequisites:
            if prerequisite not in position:
                issues.append(
                    Issue(
                        "E",
                        "E-PREREQ-MISSING",
                        f"пререквизит «{prerequisite}» не найден в плане",
                        lesson.id,
                    )
                )
            elif position[prerequisite] >= index:
                issues.append(
                    Issue(
                        "E",
                        "E-PREREQ-ORDER",
                        f"пререквизит «{prerequisite}» идёт не раньше занятия",
                        lesson.id,
                    )
                )
    return issues


def _file_issues(plan: Plan, root: Path) -> list[Issue]:
    issues: list[Issue] = []
    listed: set[str] = set()
    for lesson in plan.lessons:
        if lesson.file:
            listed.add(lesson.file)
            if not (root / lesson.file).exists():
                issues.append(
                    Issue(
                        "E",
                        "E-FILE-MISSING",
                        f"файл «{lesson.file}» не найден",
                        lesson.id,
                    )
                )
            elif lesson.planned:
                issues.append(
                    Issue(
                        "W",
                        "W-PLANNED-EXISTS",
                        f"файл «{lesson.file}» уже есть, а занятие помечено planned",
                        lesson.id,
                    )
                )
        if not lesson.sources:
            issues.append(
                Issue("W", "W-SOURCES", "у занятия не указаны источники", lesson.id)
            )
    known_outcomes = {str(item.get("id")) for item in plan.outcomes}
    for lesson in plan.lessons:
        for outcome in lesson.outcomes:
            if outcome not in known_outcomes:
                issues.append(
                    Issue(
                        "W",
                        "W-OUTCOME-UNKNOWN",
                        f"результат «{outcome}» отсутствует в outcomes плана",
                        lesson.id,
                    )
                )
    for section in plan.sections:
        if not any(lesson.kind == "practice" for lesson in section.lessons):
            issues.append(
                Issue(
                    "W",
                    "W-SECTION-NO-PRACTICE",
                    f"в разделе {section.number} нет практических занятий",
                )
            )
        covered = {
            prerequisite
            for lesson in section.lessons
            if lesson.kind == "practice"
            for prerequisite in lesson.prerequisites
        }
        for lesson in section.lessons:
            if lesson.kind == "lecture" and lesson.id not in covered:
                issues.append(
                    Issue(
                        "W",
                        "W-LECTURE-NO-PRACTICE",
                        "лекцию не закрепляет ни одна практика",
                        lesson.id,
                    )
                )
    course_root = root / "course"
    if course_root.is_dir():
        for path in sorted(course_root.rglob("*.md")):
            relative = path.relative_to(root).as_posix()
            if relative not in listed:
                issues.append(
                    Issue("W", "W-ORPHAN", f"файл «{relative}» не указан в плане")
                )
    return issues


def validate_plan(plan: Plan, root: Path) -> list[Issue]:
    issues = _hours_issues(plan) + _order_issues(plan) + _file_issues(plan, root)
    return issues


def load_plan(path: Path) -> Plan:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PlanError(f"{path}: не разбирается как YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise PlanError(f"{path}: корень plan.yml должен быть словарём")
    schema = raw.get("schema")
    if schema != PLAN_SCHEMA:
        raise PlanError(
            f"{path}: schema {schema!r} не поддерживается, ожидается {PLAN_SCHEMA}"
        )
    return Plan(
        schema=PLAN_SCHEMA,
        course={str(key): str(value) for key, value in (raw.get("course") or {}).items()},
        hours={
            str(key): int(value) for key, value in (raw.get("hours") or {}).items()
        },
        outcomes=tuple(raw.get("outcomes") or ()),
        sections=tuple(_section(item) for item in raw.get("sections") or ()),
    )
