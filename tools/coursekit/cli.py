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
    docx.add_argument("--config", default="course.yml", help="файл конфигурации курса")
    docx.add_argument("--source", default="course", help="каталог исходников")
    docx.add_argument("--normalized", default="build/normalized", help="каталог нормализованных файлов")
    docx.add_argument("--out", default="dist/docx", help="каталог результатов")

    qa = sub.add_parser("qa", help="проверить корпус")
    qa.add_argument("--strict", action="store_true", help="падать и на WARN")

    sub.add_parser("clean", help="удалить build и dist")

    build = sub.add_parser("build", help="полная сборка")
    _add_common(build)

    return parser


def _run_docx(args: argparse.Namespace) -> int:
    from pathlib import Path

    from coursekit.config import artifact_name, load_config
    from coursekit.model import parse_document
    from coursekit.normalize import normalize_tree
    from coursekit.render_docx import build_docx

    cfg = load_config(Path(args.config))
    normalized = Path(args.normalized)
    normalize_tree(Path(args.source), normalized)

    docs = [
        parse_document(path.read_text(encoding="utf-8"), path)
        for path in sorted(normalized.rglob("*.md"))
    ]
    if args.section is not None:
        docs = [doc for doc in docs if f"Раздел {args.section}" in str(doc.path)]

    out_dir = Path(args.out)
    for doc in docs:
        name = artifact_name(cfg, doc) + ".docx"
        build_docx(doc, cfg, out_dir / name, Path("build/docx-work"))
        print(name)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "docx":
        return _run_docx(args)
    print(f"{args.command}: не реализовано")
    return 2
