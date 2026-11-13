import os
from pathlib import Path

import pytest

from coursekit.cli import build


@pytest.mark.integration
def test_build_only_docx_section_one():
    root = Path(__file__).resolve().parents[3]
    os.chdir(root)
    if not list(Path("course").glob("Раздел 1*/*.md")):
        pytest.skip("в корпусе нет раздела 1")
    code = build(section=1, only={"docx"}, book=False)
    assert code == 0
    assert list(Path("dist/docx").glob("*-r1-*.docx"))


@pytest.mark.integration
def test_build_writes_qa_report():
    root = Path(__file__).resolve().parents[3]
    os.chdir(root)
    build(section=1, only={"qa"}, book=False)
    assert Path("dist/qa-report.md").exists()
