"""Разбор календарно-тематического плана в машинный снимок ktp.yml."""

from __future__ import annotations

import html
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

KTP_SCHEMA = 1

_SECTION_RE = re.compile(r"^Раздел\s+(\d+)\.\s*(.+)$")
_ROW_RE = re.compile(r"<tr[^>]*>.*?</tr>", re.S)
_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
_TAG_RE = re.compile(r"<[^>]+>")
_NUMBER_RE = re.compile(r"(\d+)")

_KIND_RULES = (
    ("Практическая работа", "practice"),
    ("Самостоятельная работа", "selfstudy"),
    ("Курсовое проектирование", "coursedesign"),
    ("Консультация", "consultation"),
    ("Экзамен", "exam"),
    ("Лекция", "lecture"),
)


class KtpError(Exception):
    """Ошибка разбора КТП."""


def _text(cell: str) -> str:
    plain = _TAG_RE.sub(" ", cell)
    return re.sub(r"\s+", " ", html.unescape(plain)).strip()


def _kind(title: str, type_text: str) -> str:
    haystack = f"{type_text} {title}".lower()
    for marker, kind in _KIND_RULES:
        if marker.lower() in haystack:
            return kind
    return "lecture"


def _lesson_number(title: str) -> int | None:
    match = re.search(r"(?:работа|Лекция)\s+(\d+)", title, re.I)
    if not match:
        return None
    return int(match.group(1))


def parse_ktp_html(text: str) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    counters: dict[str, int] = {}
    for row in _ROW_RE.findall(text):
        cells = [_text(cell) for cell in _CELL_RE.findall(row)]
        if not cells or cells[0] == "№":
            continue
        non_empty = [cell for cell in cells if cell]
        section_match = _SECTION_RE.match(non_empty[0]) if len(non_empty) == 1 else None
        if section_match:
            current = {
                "number": int(section_match.group(1)),
                "title": section_match.group(2).strip(),
                "lessons": [],
            }
            sections.append(current)
            continue
        if not cells[0].isdigit():
            continue
        if current is None:
            current = {"number": 1, "title": "", "lessons": []}
            sections.append(current)
        title = cells[1] if len(cells) > 1 else ""
        hours_text = cells[2] if len(cells) > 2 else ""
        type_text = cells[3] if len(cells) > 3 else ""
        hours_match = _NUMBER_RE.search(hours_text)
        kind = _kind(title, type_text)
        number = _lesson_number(title)
        if number is None:
            counters[kind] = counters.get(kind, 0) + 1
            number = counters[kind]
        else:
            counters[kind] = max(counters.get(kind, 0), number)
        current["lessons"].append(
            {
                "kind": kind,
                "number": number,
                "title": title,
                "hours": int(hours_match.group(1)) if hours_match else 0,
            }
        )
    lessons = [lesson for section in sections for lesson in section["lessons"]]
    if not lessons:
        raise KtpError(
            "не удалось разобрать занятия: проверьте таблицу вручную"
        )
    return {
        "schema": KTP_SCHEMA,
        "source": "",
        "parsed": "pandoc-html",
        "course": {},
        "hours": {
            "total": sum(lesson["hours"] for lesson in lessons),
            "teacher": sum(lesson["hours"] for lesson in lessons),
            "theory": sum(lesson["hours"] for lesson in lessons if lesson["kind"] == "lecture"),
            "practice": sum(lesson["hours"] for lesson in lessons if lesson["kind"] == "practice"),
            "course_design": sum(
                lesson["hours"] for lesson in lessons if lesson["kind"] == "coursedesign"
            ),
            "selfstudy": sum(
                lesson["hours"] for lesson in lessons if lesson["kind"] == "selfstudy"
            ),
            "consultation": sum(
                lesson["hours"] for lesson in lessons if lesson["kind"] == "consultation"
            ),
            "exam": sum(lesson["hours"] for lesson in lessons if lesson["kind"] == "exam"),
        },
        "sections": sections,
    }


def parse_ktp_docx(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["pandoc", str(path), "-t", "html"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise KtpError(f"pandoc не смог прочитать {path}: {result.stderr.strip()}")
    return parse_ktp_html(result.stdout)


def parse_ktp(path: Path) -> dict[str, Any]:
    path = Path(path)
    if path.suffix.lower() in (".html", ".htm"):
        return parse_ktp_html(path.read_text(encoding="utf-8"))
    return parse_ktp_docx(path)


def dump_ktp(ktp: dict[str, Any], path: Path, source: str, parsed: str) -> None:
    payload = dict(ktp)
    payload["source"] = source
    payload["parsed"] = parsed
    Path(path).write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
