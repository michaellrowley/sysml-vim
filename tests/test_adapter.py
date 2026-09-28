from pathlib import Path
import shlex
import sys
from types import SimpleNamespace

import pytest

import sysml_vim.adapter as adapter_module
from sysml_vim.adapter import ParserBackendError, SysMLLspAdapter


def test_adapter_reports_disabled_mode(monkeypatch):
    monkeypatch.delenv("SYSML_LSP_COMMAND", raising=False)
    monkeypatch.setenv("SYSML_LSP_SERVER", "/missing/sysml-lsp/server.js")
    adapter = SysMLLspAdapter()

    capabilities = adapter.capabilities()
    assert capabilities["configured"] is False
    assert capabilities["mode"] == "disabled"
    with pytest.raises(ParserBackendError, match="No local subset parser or fallback"):
        adapter.parse_workspace(Path("."), [])


def test_adapter_uses_the_lsp_model_and_diagnostics_contract(monkeypatch):
    monkeypatch.setenv("SYSML_LSP_SERVER", "/missing/sysml-lsp/server.js")
    adapter = SysMLLspAdapter()
    source_file = Path("tests/fixtures/workspace/vehicle.sysml").resolve()
    response = adapter.parse_workspace(
        source_file.parent,
        [{"path": str(source_file), "text": source_file.read_text(encoding="utf-8")}],
    )

    assert response["parser"]["name"] == "SysML v2 Language Server (ANTLR)"
    assert response["parser"]["version"] == "unknown"
    assert "SysML v2 textual grammar derived from OMG KEBNF" in response["parser"]["standards"]
    assert response["files"][0]["path"] == str(source_file)
    vehicle = next(
        symbol
        for symbol in response["files"][0]["symbols"]
        if symbol["name"] == "Vehicle"
    )
    assert vehicle["ancestors"] == ["VehiclePkg"]
    assert vehicle["attributes"] == {}


def test_adapter_surfaces_language_server_startup_errors(monkeypatch):
    invalid_command = shlex.join(
        [sys.executable, "-c", "print('not an LSP server')"]
    )
    monkeypatch.setenv("SYSML_LSP_COMMAND", invalid_command)
    monkeypatch.delenv("SYSML_LSP_SERVER", raising=False)

    with pytest.raises(ParserBackendError):
        SysMLLspAdapter().parse_workspace(Path("."), [])


def test_adapter_reports_lsp_configuration(monkeypatch):
    monkeypatch.setenv(
        "SYSML_LSP_COMMAND",
        shlex.join([sys.executable, str(Path("tests/fixtures/mock_lsp_server.py").resolve())]),
    )
    monkeypatch.delenv("SYSML_LSP_SERVER", raising=False)

    capabilities = SysMLLspAdapter().capabilities()

    assert capabilities["configured"] is True
    assert capabilities["mode"] == "custom-command"
    assert capabilities["expected_parser"] == "SysML v2 Language Server (ANTLR)"
    assert "not Pilot-equivalent" in capabilities["validation_scope"]


def test_adapter_normalizes_multiline_lsp_ranges():
    converted_range = SysMLLspAdapter._convert_lsp_range(
        {
            "start": {"line": 1, "character": 8},
            "end": {"line": 2, "character": 1},
        }
    )

    assert converted_range == {"line": 2, "col": 8, "end_col": 8}


@pytest.mark.parametrize(
    ("reported_version", "configured"),
    [("v18.20.0", False), ("v20.0.0", True)],
)
def test_adapter_checks_node_major_version(
    monkeypatch, tmp_path, reported_version, configured
):
    server_path = tmp_path / "server.js"
    server_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("SYSML_LSP_SERVER", str(server_path))
    monkeypatch.delenv("SYSML_LSP_COMMAND", raising=False)
    monkeypatch.delenv("SYSML_NODE_COMMAND", raising=False)
    monkeypatch.setattr(adapter_module.shutil, "which", lambda _: "/usr/bin/node")
    monkeypatch.setattr(
        adapter_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout=reported_version,
            stderr="",
        ),
    )

    capabilities = SysMLLspAdapter().capabilities()

    assert capabilities["configured"] is configured
