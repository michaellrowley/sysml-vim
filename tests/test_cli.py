import json
import subprocess
import sys


REPO = "."


def run_cmd(args):
    proc = subprocess.run(
        [sys.executable, "-m", "sysml_vim.cli", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout


def test_cli_check_reports_diagnostics():
    code, out = run_cmd(["check", "tests/fixtures/workspace"])
    data = json.loads(out)
    assert "diagnostics" in data
    assert code in (0, 1)


def test_cli_definition_and_view():
    code, out = run_cmd(["definition", "Vehicle", "--path", "tests/fixtures/workspace"])
    data = json.loads(out)
    assert code == 0
    assert data["name"] == "Vehicle"

    code2, out2 = run_cmd([
        "view",
        "composition",
        "--path",
        "tests/fixtures/workspace",
        "--format",
        "json",
    ])
    view = json.loads(out2)
    assert code2 == 0
    assert view["type"] == "composition"
