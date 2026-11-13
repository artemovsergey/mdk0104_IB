import subprocess


def test_shot_rejects_secret_in_command_output(tmp_path):
    out = tmp_path / "shot.png"
    result = subprocess.run(
        ["node", "scripts/shot.mjs", "--command", "echo ghp_abcdefghijklmnop", "--out", str(out)],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert result.returncode == 2
    assert not out.exists()


def test_shot_rejects_secret_in_command_itself(tmp_path):
    out = tmp_path / "shot.png"
    result = subprocess.run(
        ["node", "scripts/shot.mjs", "--command", 'TOKEN="Bearer abcdefghijklmnop"; printf "ok\\n"', "--out", str(out)],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert result.returncode == 2
    assert not out.exists()
