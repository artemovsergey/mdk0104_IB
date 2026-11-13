from pathlib import Path

import pytest

from coursekit.ktp import KtpError, parse_ktp_html

FIXTURE = Path(__file__).parent / "fixtures" / "ktp" / "ktp.html"


def test_parse_ktp_extracts_sections_and_lessons():
    text = FIXTURE.read_text(encoding="utf-8")
    ktp = parse_ktp_html(text)
    assert ktp["schema"] == 1
    assert ktp["sections"][0]["number"] == 1
    kinds = {l["kind"] for s in ktp["sections"] for l in s["lessons"]}
    assert kinds <= {"lecture", "practice", "selfstudy", "coursedesign", "consultation", "exam"}
    assert sum(l["hours"] for s in ktp["sections"] for l in s["lessons"]) > 0


def test_parse_ktp_rejects_table_without_lessons():
    with pytest.raises(KtpError, match="занят"):
        parse_ktp_html("<table><tr><td>№</td><td>Тема</td></tr></table>")


def test_ktp_cli_reports_parse_error(tmp_path, capsys):
    from coursekit.cli import main

    broken = tmp_path / "ktp.html"
    broken.write_text("<table><tr><td>№</td><td>Тема</td></tr></table>", encoding="utf-8")
    assert main(["ktp", str(broken), "--out", str(tmp_path / "ktp.yml")]) == 1
    assert "занят" in capsys.readouterr().out
