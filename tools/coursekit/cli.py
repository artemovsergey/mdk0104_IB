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

    qa = sub.add_parser("qa", help="проверить корпус")
    qa.add_argument("--strict", action="store_true", help="падать и на WARN")

    sub.add_parser("clean", help="удалить build и dist")

    build = sub.add_parser("build", help="полная сборка")
    _add_common(build)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    print(f"{args.command}: не реализовано")
    return 2
