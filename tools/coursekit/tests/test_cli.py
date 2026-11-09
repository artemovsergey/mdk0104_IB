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
