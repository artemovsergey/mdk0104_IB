"""Модель учебного документа и профили разделов."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Profile:
    kind: str
    required: tuple[str, ...]
    recommended: tuple[str, ...]


PROFILES: dict[str, Profile] = {
    "lecture": Profile(
        kind="lecture",
        required=("План лекции", "Резюме", "Контрольные вопросы"),
        recommended=("Цель лекции", "Аудитория", "Материалы"),
    ),
    "practice": Profile(
        kind="practice",
        required=("Цель работы", "Ход работы", "Варианты заданий", "Критерии оценки"),
        recommended=(
            "Теоретическая часть",
            "Практический пример",
            "Контрольные вопросы",
            "Требования к репозиторию",
        ),
    ),
    "selfstudy": Profile(
        kind="selfstudy",
        required=("Цель работы", "Ход работы", "Варианты заданий", "Критерии оценки"),
        recommended=(
            "Теоретическая часть",
            "Практический пример",
            "Контрольные вопросы",
            "Требования к репозиторию",
        ),
    ),
    "exam": Profile(
        kind="exam",
        required=("Варианты заданий", "Критерии оценки"),
        recommended=("Цель работы",),
    ),
    "week-lecture": Profile(
        kind="week-lecture",
        required=("Разобранный пример",),
        recommended=("Зачем этот навык", "Термины", "Типичные ошибки"),
    ),
    "week-practice": Profile(
        kind="week-practice",
        required=("Предусловия", "Шаги", "Границы", "Критерий готовности"),
        recommended=("Резервный сценарий",),
    ),
    "week-selfcheck": Profile(kind="week-selfcheck", required=(), recommended=()),
    "week-results": Profile(kind="week-results", required=(), recommended=()),
    "meta": Profile(kind="meta", required=(), recommended=()),
}


_ALIASES = {
    "план": "План лекции",
    "план лекции": "План лекции",
    "резюме": "Резюме",
    "резюме лекции": "Резюме",
    "итоги": "Резюме",
    "цель": "Цель работы",
    "цель работы": "Цель работы",
    "тема и цель": "Цель работы",
    "цель лекции": "Цель лекции",
    "аудитория": "Аудитория",
    "материалы": "Материалы",
    "теоретическая часть": "Теоретическая часть",
    "краткая справочная информация": "Теоретическая часть",
    "теоретические сведения": "Теоретическая часть",
    "ход работы": "Ход работы",
    "порядок выполнения": "Ход работы",
    "задание": "Ход работы",
    "практический пример": "Практический пример",
    "пример практического задания": "Практический пример",
    "пример реализации": "Практический пример",
    "пример выполнения": "Практический пример",
    "варианты": "Варианты заданий",
    "варианты заданий": "Варианты заданий",
    "15 вариантов заданий": "Варианты заданий",
    "15 вариантов простых заданий": "Варианты заданий",
    "критерии оценки": "Критерии оценки",
    "критерии оценивания": "Критерии оценки",
    "контрольные вопросы": "Контрольные вопросы",
    "вопросы для самопроверки": "Контрольные вопросы",
    "требования к репозиторию": "Требования к репозиторию",
    "требования к репозиторию на gogs": "Требования к репозиторию",
    "структура репозитория": "Требования к репозиторию",
    "структура репозитория для gogs": "Требования к репозиторию",
    "структура репозитория для студента": "Требования к репозиторию",
    "структура репозитория для практической работы": "Требования к репозиторию",
    "варианты заданий (для студентов)": "Варианты заданий",
    "практический пример (образец оформления)": "Практический пример",
}


_ALIASES.update(
    {
        "разобранный пример": "Разобранный пример",
        "зачем этот навык": "Зачем этот навык",
        "термины": "Термины",
        "типичные ошибки": "Типичные ошибки",
        "предусловия": "Предусловия",
        "шаги": "Шаги",
        "границы": "Границы",
        "критерий готовности": "Критерий готовности",
        "резервный сценарий": "Резервный сценарий",
    }
)


@dataclass
class Section:
    level: int
    title: str
    canonical: str | None
    line: int
    body: str = ""


@dataclass
class Document:
    path: Path
    kind: str
    number: int
    title: str
    sections: list[Section] = field(default_factory=list)
    raw: str = ""


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_KIND_PATTERNS = (
    ("selfstudy", re.compile(r"самостоятельн", re.IGNORECASE)),
    ("practice", re.compile(r"практическ", re.IGNORECASE)),
    ("lecture", re.compile(r"лекци", re.IGNORECASE)),
    ("exam", re.compile(r"examen|экзамен", re.IGNORECASE)),
)
_NUMBER_RE = re.compile(
    r"(?:Лекция|Практическая работа|Самостоятельная работа)\s+(\d+)",
    re.IGNORECASE,
)


def _clean_title(title: str) -> str:
    cleaned = title.strip()
    for marker in ("**", "__"):
        if len(cleaned) > 4 and cleaned.startswith(marker) and cleaned.endswith(marker):
            cleaned = cleaned[2:-2].strip()
    return cleaned.rstrip(":").strip()


def detect_kind(path: Path, layout: str = "sections") -> str:
    if layout == "weeks":
        if "_template" in path.parts:
            return "meta"
        mapping = {
            "lecture.md": "week-lecture",
            "practice.md": "week-practice",
            "self-check.md": "week-selfcheck",
            "results.md": "week-results",
        }
        return mapping.get(path.name.lower(), "meta")
    name = path.name
    for kind, pattern in _KIND_PATTERNS:
        if pattern.search(name):
            return kind
    return "practice"


def detect_number(path: Path, layout: str = "sections") -> int:
    if layout == "weeks":
        for part in path.parts:
            match = re.fullmatch(r"week-(\d+)", part, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 0
    match = _NUMBER_RE.search(path.name)
    return int(match.group(1)) if match else 0


def canonical_title(title: str, kind: str | None = None) -> str | None:
    key = _clean_title(title).lower()
    key = re.sub(r"\s+", " ", key)
    canonical = _ALIASES.get(key)
    if canonical is None:
        key = re.sub(r"^\d+(?:\.\d+)*\.?\s+", "", key)
        canonical = _ALIASES.get(key)
    if canonical is None:
        for alias, value in _ALIASES.items():
            if key.startswith(alias + ":"):
                canonical = value
                break
    if canonical == "Цель работы" and kind == "lecture":
        return "Цель лекции"
    return canonical


def _headings(text: str) -> list[tuple[int, int, str]]:
    """Возвращает (номер строки, уровень, заголовок) вне блоков кода."""
    result: list[tuple[int, int, str]] = []
    fence: str | None = None
    for number, line in enumerate(text.splitlines()):
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            continue
        if fence is not None:
            continue
        match = _HEADING_RE.match(line)
        if match:
            result.append((number, len(match.group(1)), _clean_title(match.group(2))))
    return result


def parse_document(text: str, path: Path, layout: str = "sections") -> Document:
    kind = detect_kind(path, layout)
    headings = _headings(text)
    lines = text.splitlines()

    title = ""
    if headings and headings[0][1] == 1:
        title = headings[0][2]
    elif headings:
        title = headings[0][2]
    else:
        title = path.stem

    level_two = [item for item in headings if item[1] == 2]
    sections: list[Section] = []
    for index, (line_number, level, heading_title) in enumerate(level_two):
        end = level_two[index + 1][0] if index + 1 < len(level_two) else len(lines)
        body = "\n".join(lines[line_number + 1 : end]).strip()
        sections.append(
            Section(
                level=level,
                title=heading_title,
                canonical=canonical_title(heading_title, kind),
                line=line_number + 1,
                body=body,
            )
        )

    return Document(
        path=path,
        kind=kind,
        number=detect_number(path, layout),
        title=title,
        sections=sections,
        raw=text,
    )


def missing_required(doc: Document) -> list[str]:
    profile = PROFILES.get(doc.kind)
    if not profile:
        return []
    present = {section.canonical for section in doc.sections if section.canonical}
    return [name for name in profile.required if name not in present]
