import os
from pathlib import Path
import sys

from sysml_vim.adapter import OfficialPilotAdapter


def test_adapter_reports_disabled_mode(monkeypatch):
    monkeypatch.delenv("SYSML_PILOT_COMMAND", raising=False)
    monkeypatch.delenv("SYSML_PILOT_RPC_COMMAND", raising=False)
    adapter = OfficialPilotAdapter()
    caps = adapter.capabilities()
    assert caps["configured"] is False
    assert caps["mode"] == "disabled"


def test_adapter_rpc_mode_with_local_rpc(monkeypatch):
    monkeypatch.setenv("SYSML_PILOT_RPC_COMMAND", f"{sys.executable} -m sysml_vim.rpc")
    monkeypatch.delenv("SYSML_PILOT_COMMAND", raising=False)
    adapter = OfficialPilotAdapter()
    result = adapter.invoke("definition", Path("tests/fixtures/workspace"), {"name": "Vehicle"})
    assert result["ok"] is True
    assert result["result"]["name"] == "Vehicle"


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
