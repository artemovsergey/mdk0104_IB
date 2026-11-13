"""Сборка PDF через pandoc → Typst."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from coursekit.config import CourseConfig, slugify
from coursekit.model import Document
from coursekit.render_docx import _IMAGE, replace_missing_images

_TEMPLATE = Path(__file__).parent / "templates" / "gost.typ"


def _run(command: list[str], error_prefix: str) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-20:])
        raise RuntimeError(f"{error_prefix}:\n{tail}")


def escape_slashes(text: str) -> str:
    """Экранирует `//` вне блоков кода: в Typst это начало комментария."""
    out: list[str] = []
    index = 0
    in_fence = False
    in_raw = False
    while index < len(text):
        if text.startswith("```", index):
            in_fence = not in_fence
            out.append("```")
            index += 3
            continue
        char = text[index]
        if in_fence:
            out.append(char)
            index += 1
            continue
        if char == "`":
            in_raw = not in_raw
            out.append(char)
            index += 1
            continue
        if (
            not in_raw
            and text.startswith("//", index)
            and (index == 0 or text[index - 1] != ":")
        ):
            out.append("\\/\\/")
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _to_root_relative(markdown: str, root: Path) -> str:
    """Переводит абсолютные пути картинок в пути от корня Typst (/dist/...)."""
    root = root.resolve()

    def repl(match: re.Match[str]) -> str:
        alt = match.group(1)
        target = match.group(2).strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        path = Path(target)
        if not path.is_absolute():
            return match.group(0)
        try:
            rel = path.resolve().relative_to(root)
        except ValueError:
            return match.group(0)
        return f"![{alt}](/{rel.as_posix()})"

    return _IMAGE.sub(repl, markdown)


def build_pdf(
    doc: Document,
    cfg: CourseConfig,
    out: Path,
    workdir: Path,
    toc: bool = True,
    subtitle: str = "",
) -> Path:
    if not shutil.which("typst"):
        raise RuntimeError("typst не найден в PATH")
    workdir.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)

    stem = slugify(doc.title)
    md_path = workdir / f"{stem}.md"
    typ_path = workdir / f"{stem}.typ"
    root = Path(os.path.commonpath([workdir.resolve(), out.resolve()]))
    body = replace_missing_images(doc.raw, doc)
    body = _to_root_relative(body, root)
    md_path.write_text(body + "\n", encoding="utf-8")

    pandoc_cmd = [
        "pandoc",
        str(md_path),
        "-t",
        "typst",
        "--standalone",
        f"--template={_TEMPLATE}",
        "-o",
        str(typ_path),
        "--highlight-style=tango",
    ]
    if toc:
        pandoc_cmd += ["--toc", "--toc-depth=2"]

    _run(
        pandoc_cmd,
        "pandoc не смог собрать Typst (нужен pandoc ≥ 3.1.1)",
    )

    typ_path.write_text(
        escape_slashes(typ_path.read_text(encoding="utf-8")), encoding="utf-8"
    )

    _run(
        [
            "typst",
            "compile",
            "--root",
            str(root),
            str(typ_path.resolve()),
            str(out.resolve()),
            "--input",
            f"code={cfg.code}",
            "--input",
            f"title={doc.title}",
            "--input",
            f"specialty={cfg.specialty}",
            "--input",
            f"group={cfg.group}",
            "--input",
            f"teacher={cfg.teacher}",
            "--input",
            f"year={cfg.year}",
            "--input",
            f"subtitle={subtitle}",
        ],
        "typst не смог собрать PDF",
    )
    return out
