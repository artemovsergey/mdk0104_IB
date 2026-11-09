import json
from pathlib import Path

from coursekit.manifest import write_manifest
from coursekit.model import parse_document
from coursekit.render_book import build_book_md


def _doc(md: str, name: str):
    return parse_document(md, Path(name))


def test_book_contains_docs_in_order_with_breaks():
    docs = [
        _doc("# Лекция 1\n\n## 1. А\n", "Раздел 1/Лекция 1.md"),
        _doc("# Лекция 2\n\n## 1. Б\n", "Раздел 1/Лекция 2.md"),
    ]
    book = build_book_md(docs)
    assert book.index("Лекция 1") < book.index("Лекция 2")
    assert book.count("<!-- pagebreak -->") == 1


def test_manifest_has_sha256(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_text("привет", encoding="utf-8")
    out = tmp_path / "manifest.json"
    write_manifest([f], out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["files"][0]["name"] == "a.txt"
    assert len(data["files"][0]["sha256"]) == 64
    assert data["files"][0]["size"] == 12
