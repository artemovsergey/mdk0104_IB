"""Проверки качества корпуса и отчёт."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from coursekit.model import Document, missing_required

_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_LINK = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_STALE = re.compile(
    r"net[89]\.0|visual studio|chromedriver|docker", re.IGNORECASE
)
_TODO = re.compile(r"\b(TODO|FIXME|XXX)\b")
_CYRILLIC = re.compile(r"[А-Яа-яЁё]")


@dataclass(frozen=True)
class Issue:
    level: str
    code: str
    file: str
    line: int
    message: str


def _mask_code(lines: list[str]) -> tuple[list[bool], list[tuple[int, str, int | None]]]:
    mask = [False] * len(lines)
    fences: list[tuple[int, str, int | None]] = []
    open_at: int | None = None
    open_info = ""
    open_marker = ""
    for number, line in enumerate(lines):
        match = _FENCE.match(line)
        if match:
            mask[number] = True
            marker = match.group(1)
            if open_at is None:
                open_at = number
                open_info = match.group(2).strip()
                open_marker = marker
            elif marker[0] == open_marker[0] and len(marker) >= len(open_marker):
                fences.append((open_at, open_info, number))
                open_at = None
            continue
        if open_at is not None:
            mask[number] = True
    if open_at is not None:
        fences.append((open_at, open_info, None))
    return mask, fences


def _resolve(doc: Document, root: Path, target: str) -> Path | None:
    target = target.split("#", 1)[0].strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if not target or target.startswith(("http://", "https://", "mailto:", "tel:")):
        return None
    path = Path(target)
    if path.is_absolute():
        return path
    base = doc.path.parent
    if str(base) in ("", "."):
        base = root
    return base / path


def _line_of(text: str, fragment: str, start: int = 0) -> int:
    index = text.find(fragment, start)
    if index < 0:
        return 0
    return text.count("\n", 0, index) + 1


def run_qa(docs: list[Document], root: Path) -> list[Issue]:
    issues: list[Issue] = []
    for doc in docs:
        file = str(doc.path)
        lines = doc.raw.splitlines()
        mask, fences = _mask_code(lines)

        h1 = [
            number
            for number, line in enumerate(lines)
            if not mask[number] and re.match(r"^#\s+\S", line)
        ]
        if len(h1) != 1:
            issues.append(
                Issue(
                    "ERROR",
                    "H1_COUNT",
                    file,
                    h1[1] + 1 if len(h1) > 1 else 1,
                    f"ожидается один H1, найдено {len(h1)}",
                )
            )

        for line_number, info, closed in fences:
            if closed is None:
                issues.append(
                    Issue("ERROR", "FENCE_UNCLOSED", file, line_number + 1, "блок кода не закрыт")
                )
            if not info:
                issues.append(
                    Issue(
                        "WARN",
                        "CODE_NO_LANG",
                        file,
                        line_number + 1,
                        "у блока кода не указан язык",
                    )
                )

        for number, line in enumerate(lines):
            if mask[number]:
                continue
            for match in _IMAGE.finditer(line):
                target = match.group(2)
                resolved = _resolve(doc, root, target)
                if resolved is not None and not resolved.exists():
                    issues.append(
                        Issue(
                            "WARN",
                            "IMAGE_MISSING",
                            file,
                            number + 1,
                            f"нет файла изображения: {target}",
                        )
                    )
            for match in _LINK.finditer(line):
                target = match.group(2)
                resolved = _resolve(doc, root, target)
                if resolved is not None and not resolved.exists():
                    issues.append(
                        Issue(
                            "ERROR",
                            "LINK_BROKEN",
                            file,
                            number + 1,
                            f"битая ссылка: {target}",
                        )
                    )
            if _STALE.search(line):
                issues.append(
                    Issue(
                        "WARN",
                        "STALE_STACK",
                        file,
                        number + 1,
                        "упоминание устаревшего стека",
                    )
                )
            if _TODO.search(line):
                issues.append(
                    Issue("WARN", "TODO", file, number + 1, "незакрытая пометка TODO/FIXME")
                )
            if (
                "|" not in line.strip()[:1]
                and not re.match(r"^\s*(\d+\.|[-*+])\s{2,}", line)
                and re.search(r"\S {2,}\S", line)
                and not line.lstrip().startswith(("-", "*", "+"))
            ):
                issues.append(
                    Issue("WARN", "DOUBLE_SPACE", file, number + 1, "двойной пробел в тексте")
                )

        for name in missing_required(doc):
            issues.append(
                Issue(
                    "WARN",
                    "SECTION_MISSING",
                    file,
                    _line_of(doc.raw, doc.title) if doc.title else 1,
                    f"отсутствует раздел «{name}»",
                )
            )

        if len(doc.raw.strip()) < 300:
            issues.append(
                Issue("WARN", "LEN_SHORT", file, 1, "документ короче 300 знаков")
            )
        if doc.kind == "lecture" and len(doc.raw) > 35_000:
            issues.append(
                Issue("WARN", "LEN_LONG", file, 1, "лекция длиннее 35 000 знаков")
            )

        quote_line = next(
            (
                number + 1
                for number, line in enumerate(lines)
                if not mask[number] and '"' in line and _CYRILLIC.search(line)
            ),
            None,
        )
        if quote_line is not None:
            issues.append(
                Issue(
                    "WARN",
                    "QUOTES",
                    file,
                    quote_line,
                    "прямые кавычки в русском тексте",
                )
            )

    issues.sort(key=lambda item: (item.file, item.line, item.code))
    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(issue.level == "ERROR" for issue in issues)


def render_report(issues: list[Issue], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    errors = sum(1 for issue in issues if issue.level == "ERROR")
    warnings = sum(1 for issue in issues if issue.level == "WARN")
    by_code = Counter((issue.level, issue.code) for issue in issues)

    lines = [
        "# QA-отчёт по учебным материалам",
        "",
        f"Всего замечаний: **{len(issues)}** (ERROR: {errors}, WARN: {warnings}).",
        "",
        "## Сводка",
        "",
        "| Уровень | Код | Количество |",
        "| --- | --- | --- |",
    ]
    for (level, code), count in sorted(by_code.items()):
        lines.append(f"| {level} | {code} | {count} |")

    lines.extend(["", "## Замечания", "", "| Файл | Строка | Уровень | Код | Сообщение |", "| --- | --- | --- | --- | --- |"])
    for issue in issues:
        message = issue.message.replace("|", "\\|")
        lines.append(
            f"| {issue.file} | {issue.line} | {issue.level} | {issue.code} | {message} |"
        )

    debt = [issue for issue in issues if issue.code == "SECTION_MISSING"]
    lines.extend(["", "## Долговой список", ""])
    if debt:
        for issue in debt:
            lines.append(f"- `{issue.file}`: {issue.message}")
    else:
        lines.append("Нет.")

    images = [issue for issue in issues if issue.code == "IMAGE_MISSING"]
    lines.extend(["", "## Недостающие изображения", ""])
    if images:
        for issue in images:
            lines.append(f"- `{issue.file}`: {issue.message}")
    else:
        lines.append("Нет.")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
