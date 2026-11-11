import shutil
import subprocess
from pathlib import Path

import pytest

from coursekit.config import load_config
from coursekit.model import parse_document
from coursekit.render_pdf import build_pdf, escape_slashes

pytestmark = pytest.mark.skipif(shutil.which("typst") is None, reason="typst не установлен")


def test_escape_slashes_outside_code():
    assert escape_slashes("#text[foo // bar]") == "#text[foo \\/\\/ bar]"
    assert escape_slashes("```\na // b\n```") == "```\na // b\n```"
    assert escape_slashes('#link("https://x")[t]') == '#link("https://x")[t]'
    assert escape_slashes("`a // b`") == "`a // b`"


def _pdfinfo(path: Path) -> str:
    return subprocess.run(
        ["pdfinfo", str(path)], capture_output=True, text=True, check=True
    ).stdout


@pytest.mark.integration
def test_pdf_is_a4_and_has_cyrillic(tmp_path: Path):
    md = "# Лекция 1. Основы\n\n## 1. Введение\nПроверка кириллицы: ёжик, щука, юла.\n"
    doc = parse_document(md, Path("Лекция 1.md"))
    out = build_pdf(doc, load_config(Path("course.yml")), tmp_path / "l1.pdf", tmp_path)
    info = _pdfinfo(out)
    assert "A4" in info and "595" in info
    text = subprocess.run(
        ["pdftotext", str(out), "-"], capture_output=True, text=True, check=True
    ).stdout
    assert "ёжик" in text


@pytest.mark.integration
def test_table_cell_with_double_slash_builds(tmp_path: Path):
    md = (
        "# Лекция 1\n\n## 1. Таблица\n\n"
        "| Код | Комментарий |\n|---|---|\n"
        "| `x` | `byte b = 0xFF;` // формат |\n"
    )
    doc = parse_document(md, Path("Лекция 1.md"))
    out = build_pdf(doc, load_config(Path("course.yml")), tmp_path / "t.pdf", tmp_path)
    assert out.exists() and out.stat().st_size > 1000


@pytest.mark.integration
def test_long_code_line_does_not_break_layout(tmp_path: Path):
    md = "# Лекция 1\n\n## 1. Код\n\n```csharp\n" + "var x = " + "1 + " * 60 + "1;\n```\n"
    doc = parse_document(md, Path("Лекция 1.md"))
    out = build_pdf(doc, load_config(Path("course.yml")), tmp_path / "l1.pdf", tmp_path)
    assert out.exists() and out.stat().st_size > 1000
