import json
import os
from types import SimpleNamespace
import subprocess
import sys

from sysml_vim import cli


REPO = "."


def run_cmd(args, env=None):
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    proc = subprocess.run(
        [sys.executable, "-m", "sysml_vim.cli", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
        env=merged_env,
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


def test_cli_svg_view_branch_with_mock(monkeypatch, capsys):
    monkeypatch.setattr(cli, "render_svg", lambda _: "<svg>ok</svg>")
    args = SimpleNamespace(
        type="composition",
        focus=None,
        depth=1,
        path="tests/fixtures/workspace",
        format="svg",
        official=False,
    )
    rc = cli.cmd_view(args)
    captured = capsys.readouterr()
    assert rc == 0
    assert "<svg>ok</svg>" in captured.out


def test_cli_official_status_and_rpc_official_mode():
    code, out = run_cmd(["official-status"])
    status = json.loads(out)
    assert "mode" in status

    code2, out2 = run_cmd(
        ["definition", "Vehicle", "--path", "tests/fixtures/workspace", "--official"],
        env={"SYSML_PILOT_RPC_COMMAND": f"{sys.executable} -m sysml_vim.rpc"},
    )
    payload = json.loads(out2)
    assert code2 == 0
    assert payload["mode"] == "official"
    assert payload["result"]["name"] == "Vehicle"
