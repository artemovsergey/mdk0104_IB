"""Импорт плана из существующего корпуса и генерация каркаса."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from coursekit.plan import PLAN_SCHEMA, Lesson, Plan, Section

_SECTION_RE = re.compile(r"^Раздел\s+(\d+)\.\s*(.+)$")
_LESSON_RE = re.compile(
    r"^(Лекция|Практическая работа|Самостоятельная работа)\s+(\d+)\.\s*(.+)$"
)

_KIND_BY_PREFIX = {
    "Лекция": ("lecture", "l"),
    "Практическая работа": ("practice", "p"),
    "Самостоятельная работа": ("selfstudy", "s"),
}

_PREFIX_BY_KIND = {kind: prefix for prefix, (kind, _letter) in _KIND_BY_PREFIX.items()}
_LEADING_PREFIX_RE = re.compile(
    r"^(?:Лекция|Практическая работа|Самостоятельная работа)\s+\d+\.\s*"
)


def _planned_file(section_number: int, section_title: str, kind: str, number: int, title: str) -> str | None:
    prefix = _PREFIX_BY_KIND.get(kind)
    if prefix is None:
        return None
    short = _LEADING_PREFIX_RE.sub("", title).strip() or str(number)
    return f"course/Раздел {section_number}. {section_title}/{prefix} {number}. {short}.md"


def _parse_section(directory: Path) -> tuple[int, str] | None:
    match = _SECTION_RE.match(directory.name)
    if not match:
        return None
    return int(match.group(1)), match.group(2).strip()


def _parse_lesson(path: Path) -> tuple[str, int, str, str] | None:
    match = _LESSON_RE.match(path.stem)
    if not match:
        return None
    prefix, number, title = match.group(1), int(match.group(2)), match.group(3).strip()
    kind, letter = _KIND_BY_PREFIX[prefix]
    return kind, number, title, letter


def _ktp_hours(ktp: dict[str, Any] | None) -> dict[tuple[int, str, int], int]:
    hours: dict[tuple[int, str, int], int] = {}
    if not ktp:
        return hours
    for section in ktp.get("sections") or ():
        number = int(section.get("number", 0))
        for raw in section.get("lessons") or ():
            key = (number, str(raw.get("kind")), int(raw.get("number", 0)))
            hours[key] = int(raw.get("hours", 0))
    return hours


def _ktp_sections(ktp: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not ktp:
        return {}
    return {int(section.get("number", 0)): section for section in ktp.get("sections") or ()}


def import_plan(root: Path, ktp: dict[str, Any] | None = None) -> Plan:
    root = Path(root)
    hours_map = _ktp_hours(ktp)
    ktp_sections = _ktp_sections(ktp)
    collected: dict[int, dict[str, Any]] = {}
    for path in sorted((root / "course").rglob("*.md")):
        parsed_section = _parse_section(path.parent)
        parsed_lesson = _parse_lesson(path)
        if parsed_section is None or parsed_lesson is None:
            continue
        section_number, section_title = parsed_section
        kind, number, title, letter = parsed_lesson
        bucket = collected.setdefault(
            section_number,
            {"title": section_title, "lessons": []},
        )
        bucket["lessons"].append(
            {
                "id": f"{section_number}-{letter}{number}",
                "kind": kind,
                "number": number,
                "title": title,
                "hours": hours_map.get((section_number, kind, number), 0),
                "file": path.relative_to(root).as_posix(),
            }
        )
    for section_number, raw in ktp_sections.items():
        bucket = collected.setdefault(
            section_number,
            {"title": str(raw.get("title", "")), "lessons": []},
        )
        existing = {(item["kind"], item["number"]) for item in bucket["lessons"]}
        letter_by_kind = {kind: letter for kind, letter in _KIND_BY_PREFIX.values()}
        for item in raw.get("lessons") or ():
            key = (str(item.get("kind")), int(item.get("number", 0)))
            if key in existing:
                continue
            title = str(item.get("title", ""))
            bucket["lessons"].append(
                {
                    "id": f"{section_number}-{letter_by_kind.get(key[0], 'x')}{key[1]}",
                    "kind": key[0],
                    "number": key[1],
                    "title": title,
                    "hours": int(item.get("hours", 0)),
                    "file": _planned_file(
                        section_number, bucket["title"], key[0], key[1], title
                    ),
                    "planned": True,
                }
            )
    sections = []
    for section_number in sorted(collected):
        bucket = collected[section_number]
        ktp_order = {
            (str(item.get("kind")), int(item.get("number", 0))): index
            for index, item in enumerate(
                (ktp_sections.get(section_number) or {}).get("lessons") or ()
            )
        }
        lessons = sorted(
            bucket["lessons"],
            key=lambda item: (
                ktp_order.get((item["kind"], item["number"]), 1000),
                item["kind"] != "lecture",
                item["number"],
            ),
        )
        last_lecture: str | None = None
        for item in lessons:
            if item["kind"] == "lecture":
                last_lecture = item["id"]
            elif item["kind"] in ("practice", "selfstudy") and last_lecture:
                item.setdefault("prerequisites", (last_lecture,))
        sections.append(
            Section(
                number=section_number,
                title=bucket["title"],
                goal="",
                lessons=tuple(
                    Lesson(
                        id=item["id"],
                        kind=item["kind"],
                        number=item["number"],
                        title=item["title"],
                        hours=item["hours"],
                        prerequisites=tuple(item.get("prerequisites", ())),
                        file=item.get("file"),
                        planned=bool(item.get("planned", False)),
                    )
                    for item in lessons
                ),
            )
        )
    hours = {
        "total": 0,
        "theory": 0,
        "practice": 0,
        "course_design": 0,
        "selfstudy": 0,
        "consultation": 0,
        "exam": 0,
    }
    if ktp:
        for key in hours:
            if key in (ktp.get("hours") or {}):
                hours[key] = int(ktp["hours"][key])
    course = {str(key): str(value) for key, value in ((ktp or {}).get("course") or {}).items()}
    config_path = root / "course.yml"
    if not course and config_path.exists():
        import yaml

        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        course = {
            str(key): str(value)
            for key, value in (config.get("course") or {}).items()
        }
    return Plan(
        schema=PLAN_SCHEMA,
        course=course,
        hours=hours,
        outcomes=(),
        sections=tuple(sections),
    )
