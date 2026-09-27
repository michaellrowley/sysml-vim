import os
from pathlib import Path
import shlex
import sys

import pytest

from sysml_vim.adapter import OfficialPilotAdapter, ParserBackendError


def test_adapter_reports_disabled_mode(monkeypatch):
    monkeypatch.delenv("SYSML_PILOT_COMMAND", raising=False)
    monkeypatch.delenv("SYSML_PILOT_RPC_COMMAND", raising=False)
    adapter = OfficialPilotAdapter()
    caps = adapter.capabilities()
    assert caps["configured"] is False
    assert caps["mode"] == "disabled"
    result = adapter.invoke("parse", Path("."), {"files": []})
    assert result["ok"] is False
    assert "No local subset parser or fallback" in result["error"]


def test_adapter_rpc_mode_can_query_backend_health(monkeypatch):
    monkeypatch.setenv("SYSML_PILOT_RPC_COMMAND", f"{sys.executable} -m sysml_vim.rpc")
    monkeypatch.delenv("SYSML_PILOT_COMMAND", raising=False)
    adapter = OfficialPilotAdapter()
    result = adapter.invoke("health", Path("tests/fixtures/workspace"), {})
    assert result["ok"] is True
    assert result["result"]["parser"]["configured"] is True


def test_adapter_parse_contract_uses_official_parser_metadata():
    adapter = OfficialPilotAdapter()
    files = [{"path": str(Path("tests/fixtures/workspace/vehicle.sysml").resolve()), "text": ""}]
    response = adapter.parse_workspace(Path("tests/fixtures/workspace"), files)

    assert response["parser"]["name"] == "SysML v2 Pilot Implementation (test double)"
    assert {"SysML 2.0", "KerML 1.0"} <= set(response["parser"]["standards"])
    assert response["files"][0]["path"] == files[0]["path"]


def test_adapter_argv_mode_with_python_snippet(monkeypatch):
    cmd = (
        f"{sys.executable} -c \"import json,sys;"
        "p=json.loads(sys.stdin.read() or '{}');"
        "print(json.dumps({'op':sys.argv[1],'ws':sys.argv[2],'payload':p}))\""
    )
    monkeypatch.setenv("SYSML_PILOT_COMMAND", cmd)
    monkeypatch.delenv("SYSML_PILOT_RPC_COMMAND", raising=False)
    adapter = OfficialPilotAdapter()
    result = adapter.invoke("check", Path("tests/fixtures/workspace"), {"x": 1})
    assert result["ok"] is True
    assert result["result"]["op"] == "check"


def test_adapter_reports_malformed_stdout(monkeypatch):
    command = shlex.join([sys.executable, "-c", "print('starting parser')"])
    monkeypatch.setenv("SYSML_PILOT_COMMAND", command)
    monkeypatch.delenv("SYSML_PILOT_RPC_COMMAND", raising=False)

    with pytest.raises(ParserBackendError, match="non-JSON output"):
        OfficialPilotAdapter().parse_workspace(Path("."), [])
