"""Командный интерфейс coursekit."""

from __future__ import annotations

import argparse


COMMANDS = ("normalize", "figures", "docx", "pdf", "pptx", "qa", "clean", "build")


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

    build = sub.add_parser("build", help="полная сборка")
    _add_common(build)

    return parser


def _add_paths(parser: argparse.ArgumentParser, out_default: str) -> None:
    parser.add_argument("--config", default="course.yml", help="файл конфигурации курса")
    parser.add_argument("--source", default="course", help="каталог исходников")
    parser.add_argument(
        "--normalized", default="build/normalized", help="каталог нормализованных файлов"
    )
    parser.add_argument("--out", default=out_default, help="каталог результатов")


def _collect(args: argparse.Namespace):
    from pathlib import Path

    from coursekit.config import load_config
    from coursekit.model import parse_document
    from coursekit.normalize import normalize_tree

    cfg = load_config(Path(args.config))
    normalized = Path(args.normalized)
    normalize_tree(Path(args.source), normalized)

    docs = [
        parse_document(path.read_text(encoding="utf-8"), path)
        for path in sorted(normalized.rglob("*.md"))
    ]
    if args.section is not None:
        docs = [doc for doc in docs if f"Раздел {args.section}" in str(doc.path)]
    return cfg, docs


def _run_docx(args: argparse.Namespace) -> int:
    from pathlib import Path

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
    from pathlib import Path

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
    from pathlib import Path

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
    from pathlib import Path

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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "docx":
        return _run_docx(args)
    if args.command == "pdf":
        return _run_pdf(args)
    if args.command == "pptx":
        return _run_pptx(args)
    if args.command == "figures":
        return _run_figures(args)
    print(f"{args.command}: не реализовано")
    return 2
