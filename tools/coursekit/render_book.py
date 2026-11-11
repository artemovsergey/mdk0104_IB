"""Сборка единого markdown-сборника из документов курса."""

from __future__ import annotations

import re
from pathlib import Path

from coursekit.config import CourseConfig
from coursekit.model import Document

_SECTION_RE = re.compile(r"Раздел\s+(\d+)")
_KIND_ORDER = {"lecture": 0, "practice": 1, "selfstudy": 2, "exam": 3}


def _section_number(doc: Document) -> int:
    for part in doc.path.parts:
        match = _SECTION_RE.search(part)
        if match:
            return int(match.group(1))
    return 99


_PAGEBREAK = "<!-- pagebreak -->"


def build_book_md(docs: list[Document], cfg: CourseConfig | None = None) -> str:
    ordered = sorted(
        docs, key=lambda doc: (_section_number(doc), _KIND_ORDER.get(doc.kind, 9), doc.number)
    )
    parts: list[str] = []
    for doc in ordered:
        parts.append(doc.raw.rstrip() + "\n")
    body = f"\n\n{_PAGEBREAK}\n\n".join(parts)

    if cfg is None:
        return body

    header = (
        "---\n"
        f'title: "{cfg.title}"\n'
        f'subtitle: "{cfg.code}"\n'
        f'author: "{cfg.teacher}"\n'
        "---\n\n"
    )
    return header + body
