from pathlib import Path

import yaml


def test_workflow_parses_and_has_build_job():
    data = yaml.safe_load(
        Path(".github/workflows/materials.yml").read_text(encoding="utf-8")
    )
    assert "build" in data["jobs"]
    steps = data["jobs"]["build"]["steps"]
    assert any("coursekit build" in str(s.get("run", "")) for s in steps)
    assert any("upload-artifact" in str(s.get("uses", "")) for s in steps)
