from pathlib import Path

from coursekit.render_figures import extract_mermaid, substitute_figures


def test_extract_mermaid_blocks():
    md = "```mermaid\ngraph TD\nA-->B\n```\n\n```csharp\nvar x=1;\n```\n"
    assert extract_mermaid(md) == ["graph TD\nA-->B"]


def test_substitute_replaces_block_with_image():
    md = "До\n\n```mermaid\ngraph TD\nA-->B\n```\n\nПосле\n"
    out = substitute_figures(md, {0: Path("build/figures/x-1.svg")})
    assert "```mermaid" not in out
    expected = Path("build/figures/x-1.svg").resolve().as_posix()
    assert f"![Схема 1](<{expected}>)" in out
