"""Сборка DOCX через pandoc и reference-шаблон."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from coursekit.config import CourseConfig, slugify
from coursekit.make_reference import build_reference_docx
from coursekit.model import Document

_TEMPLATE = Path(__file__).parent / "templates" / "titlepage.md"
_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_PAGEBREAK = "```{=openxml}\n<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>\n```"


def _fill(template: str, cfg: CourseConfig, doc: Document) -> str:
    values = {
        "code": cfg.code,
        "title": cfg.title,
        "doc_title": doc.title,
        "specialty": cfg.specialty,
        "group": cfg.group,
        "teacher": cfg.teacher,
        "year": cfg.year,
    }
    result = template
    for key, value in values.items():
        safe = value.replace("&", "&amp;").replace("<", "\\<").replace(">", "\\>")
        result = result.replace("{{ " + key + " }}", safe)
    return result


def _replace_images(markdown: str, doc: Document) -> str:
    base = doc.path.parent

    def repl(match: re.Match[str]) -> str:
        alt = match.group(1).strip() or "изображение"
        target = match.group(2)
        if target.startswith(("http://", "https://")):
            return match.group(0)
        candidate = Path(target)
        if not candidate.is_absolute():
            candidate = base / candidate
        if candidate.exists():
            return match.group(0)
        return f"> **Скриншот отсутствует:** {alt}"

    return _IMAGE.sub(repl, markdown)


def build_docx(doc: Document, cfg: CourseConfig, out: Path, workdir: Path) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)

    template = _TEMPLATE.read_text(encoding="utf-8")
    titlepage = _fill(template, cfg, doc)
    body = _replace_images(doc.raw, doc)
    body = body.replace("<!-- pagebreak -->", _PAGEBREAK)

    prepared = f"{titlepage}\n\n{_PAGEBREAK}\n\n{body}\n"
    md_path = workdir / f"{slugify(doc.title)}.md"
    md_path.write_text(prepared, encoding="utf-8")

    reference = build_reference_docx(workdir / "reference.docx")
    result = subprocess.run(
        [
            "pandoc",
            str(md_path),
            "-o",
            str(out),
            f"--reference-doc={reference}",
            "--toc",
            "--toc-depth=2",
            "--highlight-style=tango",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-20:])
        raise RuntimeError(f"pandoc завершился с ошибкой:\n{tail}")
    return out
