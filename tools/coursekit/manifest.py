"""Манифест собранных артефактов с контрольными суммами."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pdf_pages(path: Path) -> int | None:
    try:
        result = subprocess.run(
            ["pdfinfo", str(path)], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return None
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def _pptx_slides(path: Path) -> int | None:
    try:
        from pptx import Presentation

        return len(Presentation(str(path)).slides)
    except Exception:
        return None


def write_manifest(artifacts: list[Path], out: Path) -> None:
    files = []
    for path in sorted(artifacts):
        entry = {
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": _sha256(path),
        }
        if path.suffix.lower() == ".pdf":
            pages = _pdf_pages(path)
            if pages is not None:
                entry["pages"] = pages
        elif path.suffix.lower() == ".pptx":
            slides = _pptx_slides(path)
            if slides is not None:
                entry["slides"] = slides
        files.append(entry)

    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": files,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
