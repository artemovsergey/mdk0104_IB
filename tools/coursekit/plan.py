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
    for key, kind in (("consultation", "consultation"), ("exam", "exam")):
        if key not in plan.hours:
            continue
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
    total = sum(actual.values())
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
            exists = (root / lesson.file).exists()
            if not exists and not lesson.planned:
                issues.append(
                    Issue(
                        "E",
                        "E-FILE-MISSING",
                        f"файл «{lesson.file}» не найден",
                        lesson.id,
                    )
                )
            elif exists and lesson.planned:
                issues.append(
                    Issue(
                        "W",
                        "W-PLANNED-EXISTS",
                        f"файл «{lesson.file}» уже есть, а занятие помечено planned",
                        lesson.id,
                    )
                )
        elif not lesson.planned:
            issues.append(
                Issue(
                    "E",
                    "E-FILE-MISSING",
                    "у занятия нет файла материала",
                    lesson.id,
                )
            )
        if lesson.slides:
            listed.add(lesson.slides)
            if not (root / lesson.slides).exists():
                issues.append(
                    Issue(
                        "E",
                        "E-FILE-MISSING",
                        f"файл презентации «{lesson.slides}» не найден",
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


def load_ktp(path: Path) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PlanError(f"{path}: КТП не разбирается как YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise PlanError(f"{path}: корень ktp.yml должен быть словарём")
    return raw


def _section_lessons(section: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in section.get("lessons") or ()]


def compare_with_ktp(plan: Plan, ktp: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    plan_sections = {section.number: section for section in plan.sections}
    ktp_sections = {
        int(section["number"]): section for section in ktp.get("sections") or ()
    }
    for number in sorted(set(plan_sections) | set(ktp_sections)):
        plan_section = plan_sections.get(number)
        ktp_section = ktp_sections.get(number)
        if ktp_section is None:
            if plan_section is not None:
                for lesson in plan_section.lessons:
                    issues.append(
                        Issue(
                            "D",
                            "D-ADDED",
                            f"раздел {number}: занятие «{lesson.title}» добавлено относительно КТП",
                            lesson.id,
                        )
                    )
            continue
        if plan_section is None:
            for raw in _section_lessons(ktp_section):
                issues.append(
                    Issue(
                        "D",
                        "D-REMOVED",
                        f"раздел {number}: занятие «{raw.get('title')}» убрано из плана",
                    )
                )
            continue
        plan_by_key = {
            (lesson.kind, lesson.number): lesson for lesson in plan_section.lessons
        }
        ktp_by_key: dict[tuple[str, int], dict[str, Any]] = {}
        ktp_index: dict[tuple[str, int], int] = {}
        for index, raw in enumerate(_section_lessons(ktp_section)):
            key = (str(raw.get("kind")), int(raw.get("number", 0)))
            ktp_by_key[key] = raw
            ktp_index[key] = index
        plan_index = {
            (lesson.kind, lesson.number): index
            for index, lesson in enumerate(plan_section.lessons)
        }
        for key, lesson in plan_by_key.items():
            raw = ktp_by_key.get(key)
            if raw is None:
                issues.append(
                    Issue(
                        "D",
                        "D-ADDED",
                        f"раздел {number}: занятие «{lesson.title}» добавлено относительно КТП",
                        lesson.id,
                    )
                )
                continue
            ktp_hours = int(raw.get("hours", 0))
            if ktp_hours != lesson.hours:
                issues.append(
                    Issue(
                        "D",
                        "D-HOURS",
                        f"раздел {number}: «{lesson.title}» — часы {ktp_hours} → {lesson.hours}",
                        lesson.id,
                    )
                )
            if ktp_index[key] != plan_index[key]:
                issues.append(
                    Issue(
                        "D",
                        "D-MOVED",
                        f"раздел {number}: «{lesson.title}» переставлено "
                        f"({ktp_index[key] + 1} → {plan_index[key] + 1})",
                        lesson.id,
                    )
                )
        for key, raw in ktp_by_key.items():
            if key not in plan_by_key:
                issues.append(
                    Issue(
                        "D",
                        "D-REMOVED",
                        f"раздел {number}: занятие «{raw.get('title')}» убрано из плана",
                    )
                )
        for kind in LESSON_KINDS:
            plan_count = sum(1 for lesson in plan_section.lessons if lesson.kind == kind)
            ktp_count = sum(
                1 for key in ktp_by_key if key[0] == kind
            )
            if plan_count != ktp_count:
                issues.append(
                    Issue(
                        "D",
                        "D-COUNT",
                        f"раздел {number}: занятий вида «{kind}» "
                        f"в КТП {ktp_count}, в плане {plan_count}",
                    )
                )
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
            f"{path}: schema {schema!r}: неподдерживаемая схема плана, "
            f"ожидается {PLAN_SCHEMA}"
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


def dump_plan(plan: Plan, path: Path) -> None:
    payload = {
        "schema": plan.schema,
        "course": dict(plan.course),
        "hours": dict(plan.hours),
        "outcomes": [dict(item) for item in plan.outcomes],
        "sections": [
            {
                "number": section.number,
                "title": section.title,
                "goal": section.goal,
                "lessons": [
                    {
                        "id": lesson.id,
                        "kind": lesson.kind,
                        "number": lesson.number,
                        "title": lesson.title,
                        "hours": lesson.hours,
                        "prerequisites": list(lesson.prerequisites),
                        "outcomes": list(lesson.outcomes),
                        "sources": list(lesson.sources),
                        "file": lesson.file,
                        "slides": lesson.slides,
                        "planned": lesson.planned,
                    }
                    for lesson in section.lessons
                ],
            }
            for section in plan.sections
        ],
    }
    Path(path).write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _skeleton(lesson: Lesson) -> str:
    from coursekit.model import PROFILES

    profile = PROFILES.get(lesson.kind)
    lines = [f"# {lesson.title}", ""]
    titles = profile.required if profile else ()
    if not titles:
        lines.extend(["TODO", ""])
    for title in titles:
        lines.extend([f"## {title}", "", "TODO", ""])
    return "\n".join(lines)


def scaffold(plan: Plan, root: Path) -> list[Path]:
    created: list[Path] = []
    for lesson in plan.lessons:
        if not lesson.planned or not lesson.file:
            continue
        target = Path(root) / lesson.file
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_skeleton(lesson), encoding="utf-8")
        created.append(target)
    return created


def report_json(plan: Plan, issues: list[Issue]) -> dict[str, Any]:
    by_kind: dict[str, int] = {}
    for lesson in plan.lessons:
        by_kind[lesson.kind] = by_kind.get(lesson.kind, 0) + 1
    return {
        "schema": plan.schema,
        "summary": {
            "sections": len(plan.sections),
            "lessons": len(plan.lessons),
            "by_kind": by_kind,
            "with_file": sum(1 for lesson in plan.lessons if lesson.file),
            "planned": sum(1 for lesson in plan.lessons if lesson.planned),
            "hours": dict(plan.hours),
        },
        "issues": [
            {
                "level": issue.level,
                "code": issue.code,
                "message": issue.message,
                "lesson_id": issue.lesson_id,
            }
            for issue in issues
        ],
    }


def render_report(plan: Plan, issues: list[Issue]) -> str:
    lines = [
        f"Курс: {plan.course.get('code', '—')} {plan.course.get('title', '')}".rstrip(),
        f"Разделов: {len(plan.sections)}, занятий: {len(plan.lessons)}",
        f"Материал есть: {sum(1 for lesson in plan.lessons if lesson.file)}, "
        f"запланировано: {sum(1 for lesson in plan.lessons if lesson.planned)}",
        f"Часы: total {plan.hours.get('total', 0)}, теория {plan.hours.get('theory', 0)}, "
        f"практика {plan.hours.get('practice', 0)}, "
        f"курсовое {plan.hours.get('course_design', 0)}, "
        f"СРС {plan.hours.get('selfstudy', 0)}",
    ]
    for section in plan.sections:
        kinds: dict[str, int] = {}
        for lesson in section.lessons:
            kinds[lesson.kind] = kinds.get(lesson.kind, 0) + 1
        detail = ", ".join(f"{kind}: {count}" for kind, count in kinds.items())
        hours = sum(lesson.hours for lesson in section.lessons)
        lines.append(f"Раздел {section.number}. {section.title} — {hours} ч ({detail})")
    if issues:
        lines.append("")
        for issue in issues:
            where = f" [{issue.lesson_id}]" if issue.lesson_id else ""
            lines.append(f"{issue.level} {issue.code}{where} {issue.message}")
    return "\n".join(lines)
