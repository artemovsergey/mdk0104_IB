import subprocess
import sys


def test_cli_help_lists_commands():
    out = subprocess.run(
        [sys.executable, "-m", "coursekit", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    for cmd in ("normalize", "build", "qa", "clean"):
        assert cmd in out.stdout


def test_plan_check_fails_on_error(tmp_path, monkeypatch, capsys):
    from coursekit.cli import main
    (tmp_path / "plan.yml").write_text("schema: 1\ncourse: {}\nhours: {total: 2}\nsections: []\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert main(["plan", "--check"]) == 1
    assert "E-HOURS-TOTAL" in capsys.readouterr().out


def test_plan_check_passes_on_fixture(tmp_path, monkeypatch):
    import shutil
    from pathlib import Path
    from coursekit.cli import main
    src = Path(__file__).parent / "fixtures" / "plan"
    shutil.copytree(src, tmp_path, dirs_exist_ok=True)
    monkeypatch.chdir(tmp_path)
    assert main(["plan", "--check"]) == 0


def test_version_prints_schema(capsys):
    import pytest
    from coursekit.cli import main
    with pytest.raises(SystemExit):
        main(["--version"])
    assert "plan schema 1" in capsys.readouterr().out


def test_plan_returns_error_code_without_check_flag(tmp_path, capsys):
    from coursekit.cli import main

    plan = tmp_path / "plan.yml"
    plan.write_text(
        "schema: 1\ncourse: {}\nhours: {total: 99}\noutcomes: []\nsections: []\n",
        encoding="utf-8",
    )
    assert main(["plan", "--path", str(plan)]) == 1
    assert "E-HOURS-TOTAL" in capsys.readouterr().out


def test_plan_reports_unknown_schema(tmp_path, capsys):
    from coursekit.cli import main

    plan = tmp_path / "plan.yml"
    plan.write_text("schema: 99\ncourse: {}\nsections: []\n", encoding="utf-8")
    assert main(["plan", "--path", str(plan)]) == 1
    assert "схем" in capsys.readouterr().out
