"""Сборка PDF через pandoc → Typst."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from coursekit.config import CourseConfig, slugify
from coursekit.model import Document
from coursekit.render_docx import replace_missing_images

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


def build_pdf(doc: Document, cfg: CourseConfig, out: Path, workdir: Path) -> Path:
    if not shutil.which("typst"):
        raise RuntimeError("typst не найден в PATH")
    workdir.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)

    stem = slugify(doc.title)
    md_path = workdir / f"{stem}.md"
    typ_path = workdir / f"{stem}.typ"
    md_path.write_text(replace_missing_images(doc.raw, doc) + "\n", encoding="utf-8")

    _run(
        [
            "pandoc",
            str(md_path),
            "-t",
            "typst",
            "--standalone",
            f"--template={_TEMPLATE}",
            "-o",
            str(typ_path),
            "--toc",
            "--toc-depth=2",
            "--highlight-style=tango",
        ],
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
            str(Path(os.path.commonpath([workdir.resolve(), out.resolve()]))),
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
        ],
        "typst не смог собрать PDF",
    )
    return out
