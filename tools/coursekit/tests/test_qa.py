from pathlib import Path

from coursekit.model import parse_document
from coursekit.qa import has_errors, run_qa


def _doc(md: str, name: str = "Лекция 1.md"):
    return parse_document(md, Path(name))


def test_two_h1_is_error():
    doc = _doc("# Лекция 1\n\n# Ещё заголовок\n")
    issues = run_qa([doc], Path("."))
    assert any(i.level == "ERROR" and i.code == "H1_COUNT" for i in issues)


def test_unclosed_fence_is_error():
    doc = _doc("# Лекция 1\n\n```csharp\nvar x = 1;\n")
    issues = run_qa([doc], Path("."))
    assert any(i.level == "ERROR" and i.code == "FENCE_UNCLOSED" for i in issues)


def test_missing_image_is_warning(tmp_path: Path):
    doc = _doc("# Лекция 1\n\n![Скрин](images/none.png)\n")
    issues = run_qa([doc], tmp_path)
    assert any(i.level == "WARN" and i.code == "IMAGE_MISSING" for i in issues)
    assert not has_errors(issues)


def test_missing_section_is_warning():
    doc = _doc(
        "# Практическая работа 2. Поток\n\n## Краткая справочная информация\nТекст\n",
        "Практическая работа 2.md",
    )
    issues = run_qa([doc], Path("."))
    assert any(i.level == "WARN" and i.code == "SECTION_MISSING" for i in issues)


def test_bare_code_fence_is_warning():
    doc = _doc("# Лекция 1\n\n```\nConsole.WriteLine();\n```\n")
    issues = run_qa([doc], Path("."))
    assert any(i.level == "WARN" and i.code == "CODE_NO_LANG" for i in issues)


def test_stale_net8_is_warning():
    doc = _doc("# Лекция 1\n\nПроект на net8.0.\n")
    issues = run_qa([doc], Path("."))
    assert any(i.code == "STALE_STACK" for i in issues)


def test_broken_relative_link_is_error(tmp_path: Path):
    doc = _doc("# Лекция 1\n\n[файл](missing.md)\n")
    issues = run_qa([doc], tmp_path)
    assert any(i.level == "ERROR" and i.code == "LINK_BROKEN" for i in issues)


def test_angle_bracket_image_is_not_missing(tmp_path: Path):
    image = tmp_path / "figure.png"
    image.write_bytes(b"png")
    doc = _doc(f"# Лекция 1\n\n![Схема 1](<{image.as_posix()}>)\n")
    issues = run_qa([doc], tmp_path)
    assert not [i for i in issues if i.code == "IMAGE_MISSING"]
