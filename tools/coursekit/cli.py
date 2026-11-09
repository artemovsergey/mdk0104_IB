"""Командный интерфейс coursekit."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from coursekit.model import Document, parse_document
from coursekit.normalize import normalize_text, normalize_tree

COMMANDS = ("normalize", "figures", "docx", "pdf", "pptx", "qa", "clean", "build")

_SECTION_RE = re.compile(r"Раздел\s+(\d+)")
_KIND_ORDER = {"lecture": 0, "practice": 1, "selfstudy": 2, "exam": 3}


def _section_of(path: Path) -> int:
    for part in path.parts:
        match = _SECTION_RE.search(part)
        if match:
            return int(match.group(1))
    return 99


def collect_docs(root: Path = Path("course")) -> list[Document]:
    """Читает markdown курса, нормализует в памяти и сохраняет исходные пути."""
    docs = []
    for source in sorted(Path(root).rglob("*.md")):
        text = source.read_text(encoding="utf-8")
        normalized, _ = normalize_text(text)
        docs.append(parse_document(normalized, source))
    docs.sort(key=lambda doc: (_section_of(doc.path), _KIND_ORDER.get(doc.kind, 9), doc.number))
    return docs


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--section", type=int, default=None, help="номер раздела")
    parser.add_argument("--book", action="store_true", help="собрать сборник")
    parser.add_argument(
        "--only",
        default="",
        help="список этапов через запятую: docx,pdf,pptx,figures,qa",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coursekit",
        description="Сборка учебных материалов курса из markdown",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    normalize = sub.add_parser("normalize", help="нормализовать markdown")
    normalize.add_argument("--check", action="store_true", help="только проверить")

    for name, help_text in (
        ("figures", "собрать схемы"),
        ("docx", "собрать DOCX"),
        ("pdf", "собрать PDF"),
        ("pptx", "собрать PPTX"),
    ):
        cmd = sub.add_parser(name, help=help_text)
        _add_common(cmd)

    docx = sub.choices["docx"]
    _add_paths(docx, "dist/docx")
    pdf = sub.choices["pdf"]
    _add_paths(pdf, "dist/pdf")
    pptx = sub.choices["pptx"]
    _add_paths(pptx, "dist/pptx")
    figures = sub.choices["figures"]
    _add_paths(figures, "dist/figures")

    qa = sub.add_parser("qa", help="проверить корпус")
    qa.add_argument("--strict", action="store_true", help="падать и на WARN")

    sub.add_parser("clean", help="удалить build и dist")

    build_cmd = sub.add_parser("build", help="полная сборка")
    _add_common(build_cmd)
    build_cmd.add_argument("--config", default="course.yml", help="файл конфигурации курса")
    build_cmd.add_argument("--source", default="course", help="каталог исходников")
    build_cmd.add_argument("--out", default="dist", help="каталог результатов")

    return parser


def _add_paths(parser: argparse.ArgumentParser, out_default: str) -> None:
    parser.add_argument("--config", default="course.yml", help="файл конфигурации курса")
    parser.add_argument("--source", default="course", help="каталог исходников")
    parser.add_argument(
        "--normalized", default="build/normalized", help="каталог нормализованных файлов"
    )
    parser.add_argument("--out", default=out_default, help="каталог результатов")


def _collect(args: argparse.Namespace):
    from coursekit.config import load_config

    cfg = load_config(Path(args.config))
    docs = collect_docs(Path(args.source))
    if args.section is not None:
        docs = [doc for doc in docs if _section_of(doc.path) == args.section]
    return cfg, docs


def _run_docx(args: argparse.Namespace) -> int:
    from coursekit.config import artifact_name
    from coursekit.render_docx import build_docx

    cfg, docs = _collect(args)
    out_dir = Path(args.out)
    for doc in docs:
        name = artifact_name(cfg, doc) + ".docx"
        build_docx(doc, cfg, out_dir / name, Path("build/docx-work"))
        print(name)
    return 0


def _run_pdf(args: argparse.Namespace) -> int:
    from coursekit.config import artifact_name
    from coursekit.render_pdf import build_pdf

    cfg, docs = _collect(args)
    out_dir = Path(args.out)
    for doc in docs:
        name = artifact_name(cfg, doc) + ".pdf"
        build_pdf(doc, cfg, out_dir / name, Path("build/pdf-work"))
        print(name)
    return 0


def _run_pptx(args: argparse.Namespace) -> int:
    from coursekit.config import artifact_name
    from coursekit.render_pptx import build_pptx

    cfg, docs = _collect(args)
    docs = [doc for doc in docs if doc.kind == "lecture"]
    out_dir = Path(args.out)
    for doc in docs:
        name = artifact_name(cfg, doc) + ".pptx"
        build_pptx(doc, cfg, out_dir / name)
        print(name)
    return 0


def _run_figures(args: argparse.Namespace) -> int:
    from coursekit.render_figures import build_figures

    _cfg, docs = _collect(args)
    out_dir = Path(args.out)
    total = 0
    for doc in docs:
        figures = build_figures(doc, out_dir)
        for path in figures.values():
            print(path)
        total += len(figures)
    print(f"схем: {total}")
    return 0


def _run_normalize(args: argparse.Namespace) -> int:
    from coursekit.normalize import check_normalized

    changed = check_normalized(Path("course"), Path("build/normalized"))
    if args.check:
        for path in changed:
            print(path)
        return 1 if changed else 0
    normalize_tree(Path("course"), Path("build/normalized"))
    print(f"нормализовано файлов: {len(list(Path('course').rglob('*.md')))}")
    return 0


def _run_qa(args: argparse.Namespace) -> int:
    from coursekit.qa import has_errors, render_report, run_qa

    docs = collect_docs(Path("course"))
    issues = run_qa(docs, Path("course"))
    render_report(issues, Path("dist/qa-report.md"))
    for issue in issues:
        print(f"{issue.level} {issue.file}:{issue.line} {issue.code} {issue.message}")
    if has_errors(issues):
        return 1
    if args.strict and issues:
        return 1
    return 0


def _run_clean(args: argparse.Namespace) -> int:
    for name in ("build", "dist"):
        shutil.rmtree(name, ignore_errors=True)
    print("build и dist удалены")
    return 0


def build(
    section: int | None = None,
    only: set[str] | None = None,
    book: bool = False,
    config: str = "course.yml",
    source: str = "course",
    out: str = "dist",
) -> int:
    """Полный цикл: нормализация, схемы, рендеры, QA и манифест."""
    from coursekit.config import artifact_name, load_config
    from coursekit.manifest import write_manifest
    from coursekit.qa import has_errors, render_report, run_qa
    from coursekit.render_book import build_book_md
    from coursekit.render_docx import build_docx
    from coursekit.render_figures import prepare_doc
    from coursekit.render_pdf import build_pdf
    from coursekit.render_pptx import build_pptx

    stages = set(only) if only else {"docx", "pdf", "pptx", "figures", "qa"}
    cfg = load_config(Path(config))
    source_dir = Path(source)
    dist = Path(out)
    dist.mkdir(parents=True, exist_ok=True)

    normalize_tree(source_dir, Path("build/normalized"))

    docs = collect_docs(source_dir)
    if section is not None:
        docs = [doc for doc in docs if _section_of(doc.path) == section]

    docs = [prepare_doc(doc, dist / "figures") for doc in docs]

    artifacts: list[Path] = []
    for doc in docs:
        stem = artifact_name(cfg, doc)
        if "docx" in stages:
            path = dist / "docx" / f"{stem}.docx"
            build_docx(doc, cfg, path, Path("build/docx-work"))
            artifacts.append(path)
            print(path)
        if "pdf" in stages:
            path = dist / "pdf" / f"{stem}.pdf"
            build_pdf(doc, cfg, path, Path("build/pdf-work"))
            artifacts.append(path)
            print(path)
        if "pptx" in stages and doc.kind == "lecture":
            path = dist / "pptx" / f"{stem}.pptx"
            build_pptx(doc, cfg, path)
            artifacts.append(path)
            print(path)

    if book and section is None and docs:
        book_md = build_book_md(docs)
        book_doc = parse_document(book_md, source_dir / "book.md")
        if "docx" in stages:
            path = dist / "docx" / f"{cfg.repo_slug}-book.docx"
            build_docx(book_doc, cfg, path, Path("build/docx-work"))
            artifacts.append(path)
            print(path)
        if "pdf" in stages:
            path = dist / "pdf" / f"{cfg.repo_slug}-book.pdf"
            build_pdf(book_doc, cfg, path, Path("build/pdf-work"))
            artifacts.append(path)
            print(path)

    issues = run_qa(docs, source_dir)
    render_report(issues, dist / "qa-report.md")
    if artifacts:
        write_manifest(artifacts, dist / "manifest.json")
    errors = sum(1 for issue in issues if issue.level == "ERROR")
    warnings = sum(1 for issue in issues if issue.level == "WARN")
    print(f"QA: ошибок {errors}, предупреждений {warnings}")
    return 1 if has_errors(issues) else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "normalize":
        return _run_normalize(args)
    if args.command == "qa":
        return _run_qa(args)
    if args.command == "clean":
        return _run_clean(args)
    if args.command == "build":
        only = {item.strip() for item in args.only.split(",") if item.strip()}
        return build(
            section=args.section,
            only=only or None,
            book=args.book,
            config=args.config,
            source=args.source,
            out=args.out,
        )
    if args.command == "docx":
        return _run_docx(args)
    if args.command == "pdf":
        return _run_pdf(args)
    if args.command == "pptx":
        return _run_pptx(args)
    if args.command == "figures":
        return _run_figures(args)
    return 2
