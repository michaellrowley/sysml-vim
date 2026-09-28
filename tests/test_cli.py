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

    code3, out3 = run_cmd([
        "view",
        "composition",
        "--path",
        "tests/fixtures/workspace",
        "--format",
        "graph",
        "--focus",
        "Vehicle",
    ])
    assert code3 == 0
    assert "View Graph: composition" in out3

    code4, out4 = run_cmd([
        "view",
        "composition",
        "--path",
        "tests/fixtures/workspace",
        "--format",
        "graph-json",
        "--focus",
        "Vehicle",
    ])
    graph_data = json.loads(out4)
    assert code4 == 0
    assert "graph" in graph_data
    assert graph_data["layout"]["nodes"]
    assert graph_data["layout"]["edges"]


def test_cli_svg_view_branch_with_mock(monkeypatch, capsys):
    monkeypatch.setattr(cli, "render_svg", lambda _: "<svg>ok</svg>")
    args = SimpleNamespace(
        type="composition",
        focus=None,
        depth=1,
        path="tests/fixtures/workspace",
        format="svg",
    )
    rc = cli.cmd_view(args)
    captured = capsys.readouterr()
    assert rc == 0
    assert "<svg>ok</svg>" in captured.out


def test_cli_reports_parser_status_and_uses_it_for_navigation():
    code, out = run_cmd(["parser-status"])
    status = json.loads(out)
    assert code == 0
    assert "mode" in status
    assert status["expected_parser"] == "SysML v2 Language Server (ANTLR)"
    assert status["response_validated"] is False

    code2, out2 = run_cmd(["definition", "Vehicle", "--path", "tests/fixtures/workspace"])
    payload = json.loads(out2)
    assert code2 == 0
    assert payload["name"] == "Vehicle"


def test_cli_reports_missing_parser_instead_of_using_a_subset(monkeypatch, capsys):
    monkeypatch.delenv("SYSML_LSP_COMMAND", raising=False)
    monkeypatch.setenv("SYSML_LSP_SERVER", "/missing/sysml-lsp/server.js")

    exit_code = cli.main(["check", "tests/fixtures/workspace"])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "No local subset parser or fallback" in captured.err
