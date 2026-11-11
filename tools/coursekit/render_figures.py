"""Рендер mermaid-схем в SVG/PNG и подстановка изображений в markdown."""

from __future__ import annotations

import re
import subprocess
from dataclasses import replace
from pathlib import Path

from coursekit.config import slugify
from coursekit.model import Document, parse_document

_TEMPLATE = Path(__file__).parent / "templates" / "puppeteer.json"
_BLOCK = re.compile(r"^[ \t]*(`{3,}|~{3,})mermaid[^\n]*\n(.*?)^[ \t]*\1[ \t]*$", re.M | re.S)


def extract_mermaid(text: str) -> list[str]:
    return [match.group(2).strip() for match in _BLOCK.finditer(text)]


def substitute_figures(text: str, figures: dict[int, Path]) -> str:
    counter = {"index": 0}

    def replace_block(match: re.Match[str]) -> str:
        index = counter["index"]
        counter["index"] += 1
        path = figures.get(index)
        if path is None:
            return match.group(0)
        target = path.resolve().as_posix()
        return f"![Схема {index + 1}](<{target}>)"

    return _BLOCK.sub(replace_block, text)


def _render(command: list[str], error_prefix: str) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-15:])
        raise RuntimeError(f"{error_prefix}:\n{tail}")


def build_figures(doc: Document, out_dir: Path) -> dict[int, Path]:
    blocks = extract_mermaid(doc.raw)
    if not blocks:
        return {}
    out_dir.mkdir(parents=True, exist_ok=True)
    figures: dict[int, Path] = {}
    for index, code in enumerate(blocks):
        stem = f"{slugify(doc.path.stem)}-{index + 1}"
        source = out_dir / f"{stem}.mmd"
        output = out_dir / f"{stem}.png"
        source.write_text(code + "\n", encoding="utf-8")
        _render(
            [
                "npx",
                "-y",
                "@mermaid-js/mermaid-cli@11",
                "-i",
                str(source),
                "-o",
                str(output),
                "-b",
                "transparent",
                "-s",
                "2",
                "-p",
                str(_TEMPLATE),
            ],
            f"mermaid-cli не смог отрисовать схему {doc.path.name} #{index + 1}",
        )
        figures[index] = output
    return figures


def prepare_doc(doc: Document, figures_dir: Path) -> Document:
    figures = build_figures(doc, figures_dir)
    if not figures:
        return doc
    text = substitute_figures(doc.raw, figures)
    return replace(parse_document(text, doc.path), raw=text)
