"""Конфигурация курса и имена артефактов."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from coursekit.model import Document


_TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "c",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def slugify(text: str) -> str:
    """Транслитерирует строку в ASCII-слаг."""
    parts: list[str] = []
    for char in text.lower():
        if char in _TRANSLIT:
            parts.append(_TRANSLIT[char])
        elif char.isascii() and char.isalnum():
            parts.append(char)
        else:
            parts.append("-")
    slug = re.sub(r"-+", "-", "".join(parts)).strip("-")
    return slug


@dataclass(frozen=True)
class CourseConfig:
    code: str
    title: str
    specialty: str
    group: str
    year: str
    teacher: str
    repo_slug: str
    docx: bool = True
    pdf: bool = True
    pptx: bool = True
    figures: bool = True
    book: bool = False
    layout: str = "sections"


def load_config(path: Path | str = Path("course.yml")) -> CourseConfig:
    """Читает course.yml и возвращает конфигурацию курса."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    course = data.get("course") or {}
    build = data.get("build") or {}

    missing = [key for key in ("code", "title") if not course.get(key)]
    if missing:
        raise ValueError(f"в course.yml нет обязательных полей: {', '.join(missing)}")

    return CourseConfig(
        code=str(course["code"]),
        title=str(course["title"]),
        specialty=str(course.get("specialty", "")),
        group=str(course.get("group", "")),
        year=str(course.get("year", "")),
        teacher=str(course.get("teacher", "")),
        repo_slug=str(course.get("repo_slug") or slugify(str(course["code"]))),
        docx=bool(build.get("docx", True)),
        pdf=bool(build.get("pdf", True)),
        pptx=bool(build.get("pptx", True)),
        figures=bool(build.get("figures", True)),
        book=bool(build.get("book", False)),
        layout=str(course.get("layout", "sections")),
    )


_SECTION_RE = re.compile(r"Раздел\s+(\d+)", re.IGNORECASE)
_KIND_SLUG = {
    "lecture": "lecture",
    "practice": "practice",
    "selfstudy": "selfstudy",
    "exam": "exam",
    "week-lecture": "lecture",
    "week-practice": "practice",
    "week-selfcheck": "selfcheck",
    "week-results": "results",
    "meta": "meta",
}


def artifact_name(cfg: CourseConfig, doc: "Document") -> str:
    """Возвращает ASCII-имя артефакта без расширения."""
    kind = _KIND_SLUG.get(doc.kind, "doc")
    if doc.kind == "exam":
        return f"{cfg.repo_slug}-exam"
    if cfg.layout == "weeks":
        return f"{cfg.repo_slug}-w{doc.number:02d}-{kind}"
    match = _SECTION_RE.search(str(doc.path))
    if not match:
        return f"{cfg.repo_slug}-{kind}-{doc.number:02d}"
    return f"{cfg.repo_slug}-r{int(match.group(1))}-{kind}-{doc.number:02d}"
