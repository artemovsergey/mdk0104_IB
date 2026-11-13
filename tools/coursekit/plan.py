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
