"""Сборка методички: титул, содержание, корпус, приложения, источники."""

from __future__ import annotations

import re
from pathlib import Path

from coursekit.config import CourseConfig
from coursekit.model import Document
from coursekit.render_book import build_book_md, _section_number

TITLEPAGE = Path("templates") / "titlepage.md"

_SECTION_RE = re.compile(r"Раздел\s+(\d+)")
_KIND_TITLE = {"lecture": "Лекция", "practice": "Практическая работа", "selfstudy": "Самостоятельная работа"}
_APPENDIX_RE = re.compile(r"^##\s+(Варианты заданий|Критерии оценки)\s*$", re.MULTILINE)
_TITLE_PREFIX_RE = re.compile(
    r"^(?:Лекция|Практическая работа|Самостоятельная работа)\s+\d+\.\s*", re.IGNORECASE
)


def _short_title(doc: Document) -> str:
    return _TITLE_PREFIX_RE.sub("", doc.title).strip()


def load_titlepage(root: Path | str = Path(".")) -> str | None:
    path = Path(root) / TITLEPAGE
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _section_dir(doc: Document) -> str:
    for part in doc.path.parts:
        if _SECTION_RE.search(part):
            return part
    return ""


def _toc(docs: list[Document]) -> str:
    lines = ["## Содержание", ""]
    current = None
    for doc in docs:
        section = _section_dir(doc)
        if section and section != current:
            current = section
            lines.append(f"**{section}**")
            lines.append("")
        kind = _KIND_TITLE.get(doc.kind)
        if kind:
            lines.append(f"- {kind} {doc.number}. {_short_title(doc)}")
    lines.append("")
    return "\n".join(lines)


def _appendix(docs: list[Document]) -> str:
    blocks: list[str] = []
    for doc in docs:
        if doc.kind != "practice":
            continue
        matches = list(_APPENDIX_RE.finditer(doc.raw))
        if not matches:
            continue
        parts: list[str] = []
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(doc.raw)
            parts.append(doc.raw[start:end].strip())
        blocks.append(
            f"### Практическая работа {doc.number}. {doc.title}\n\n" + "\n\n".join(parts)
        )
    if not blocks:
        return ""
    return "## Приложения\n\nВарианты заданий и критерии оценки.\n\n" + "\n\n".join(blocks) + "\n"


def _sources(sources: list[dict] | dict) -> str:
    if not sources:
        return ""
    if isinstance(sources, dict):
        items = [{"id": key, **value} for key, value in sources.items()]
    else:
        items = list(sources)
    lines = ["## Источники", ""]
    for index, source in enumerate(items, start=1):
        title = source.get("title") or source.get("id", "")
        url = source.get("url", "")
        suffix = f" — {url}" if url else ""
        lines.append(f"{index}. {title}{suffix}")
    lines.append("")
    return "\n".join(lines)


def _fill(text: str, cfg: CourseConfig | None) -> str:
    if cfg is None:
        return text
    values = {
        "code": cfg.code,
        "title": cfg.title,
        "specialty": cfg.specialty,
        "group": cfg.group,
        "teacher": cfg.teacher,
        "year": cfg.year,
    }
    for key, value in values.items():
        text = text.replace("{{ " + key + " }}", value)
    return text


def build_docs_md(
    docs: list[Document],
    cfg: CourseConfig | None = None,
    sources: list[dict] | dict | None = None,
    titlepage_text: str | None = None,
) -> str:
    parts: list[str] = []
    if titlepage_text:
        parts.append(_fill(titlepage_text, cfg).rstrip())
    else:
        parts.append(
            "# Методичка\n\n"
            "> **WARN:** титульный лист не найден (`templates/titlepage.md`), "
            "сборка черновика. Положите шаблон колледжа и повторите.\n"
        )
    parts.append(_toc(docs))
    parts.append(build_book_md(docs, cfg=None))
    appendix = _appendix(docs)
    if appendix:
        parts.append(appendix.rstrip())
    sources_md = _sources(sources or [])
    if sources_md:
        parts.append(sources_md.rstrip())
    return "\n\n".join(part for part in parts if part.strip()) + "\n"
