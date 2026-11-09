"""Нормализация markdown без изменения смысла текста."""

from __future__ import annotations

import re
from pathlib import Path

from coursekit.model import canonical_title


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_HR_RE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
_LIST_RE = re.compile(r"^(\s*)[*+]\s+(.*)$")
_NUMBERED_RE = re.compile(r"^(\d+)\.\s+(.*)$")
_SUBNUMBERED_RE = re.compile(r"^(\d+)\.(\d+)\.?\s+(.*)$")


def _strip_bold(text: str) -> str:
    stripped = text.strip()
    for marker in ("**", "__"):
        if len(stripped) > len(marker) * 2 and stripped.startswith(marker) and stripped.endswith(marker):
            return stripped[len(marker) : -len(marker)].strip()
    return stripped


def _canonical_heading(level: int, text: str) -> tuple[int, str]:
    text = _strip_bold(text).rstrip(":").strip()
    if level == 1:
        return 1, text
    if _SUBNUMBERED_RE.match(text):
        return 3, text
    if _NUMBERED_RE.match(text):
        return 2, text
    if canonical_title(text) is not None:
        return 2, text
    return min(max(level, 2), 3), text


def normalize_text(text: str) -> tuple[str, list[str]]:
    """Приводит markdown к канону. Возвращает текст и предупреждения."""
    warnings: list[str] = []
    result: list[str] = []
    fence: str | None = None
    fence_len = 0
    h1_count = 0
    previous_level = 0

    for number, line in enumerate(text.splitlines(), start=1):
        if fence is not None:
            closing = _FENCE_RE.match(line)
            if (
                closing
                and closing.group(1)[0] == fence
                and len(closing.group(1)) >= fence_len
                and not closing.group(2).strip()
            ):
                fence = None
                fence_len = 0
            result.append(line)
            continue

        opening = _FENCE_RE.match(line)
        if opening:
            fence = opening.group(1)[0]
            fence_len = len(opening.group(1))
            if not opening.group(2).strip():
                warnings.append(f"строка {number}: блок кода без языка")
            result.append(line)
            continue

        if _HR_RE.match(line):
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            level, title = _canonical_heading(len(heading.group(1)), heading.group(2))
            if level == 1:
                h1_count += 1
                if h1_count > 1:
                    warnings.append(f"строка {number}: второй заголовок первого уровня")
            elif previous_level and level > previous_level + 1:
                warnings.append(f"строка {number}: заголовок прыгнул через уровень")
            previous_level = level
            result.append(f"{'#' * level} {title}".rstrip())
            continue

        list_match = _LIST_RE.match(line)
        if list_match:
            indent = list_match.group(1)
            indent = " " * (round(len(indent) / 4) * 4)
            result.append(f"{indent}- {list_match.group(2)}")
            continue

        result.append(line)

    if fence is not None:
        warnings.append("незакрытый блок кода")

    return "\n".join(result) + "\n", warnings


def normalize_file(src: Path, dst: Path) -> list[str]:
    """Нормализует один файл и пишет результат в dst."""
    text = src.read_text(encoding="utf-8")
    normalized, warnings = normalize_text(text)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(normalized, encoding="utf-8")
    return [f"{src.name}: {warning}" for warning in warnings]


def normalize_tree(src_root: Path, dst_root: Path) -> dict[str, list[str]]:
    """Нормализует все markdown-файлы дерева. Ключи — относительные пути."""
    report: dict[str, list[str]] = {}
    for src in sorted(src_root.rglob("*.md")):
        relative = src.relative_to(src_root)
        dst = dst_root / relative
        report[relative.as_posix()] = normalize_file(src, dst)
    return report


def check_normalized(src_root: Path, dst_root: Path) -> list[Path]:
    """Возвращает файлы, которые изменились бы при нормализации."""
    changed: list[Path] = []
    for src in sorted(src_root.rglob("*.md")):
        relative = src.relative_to(src_root)
        dst = dst_root / relative
        normalized, _ = normalize_text(src.read_text(encoding="utf-8"))
        if not dst.exists() or dst.read_text(encoding="utf-8") != normalized:
            changed.append(relative)
    return changed
