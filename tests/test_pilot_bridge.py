import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

import pytest

from sysml_vim.adapter import OfficialPilotAdapter
from sysml_vim.workspace import WorkspaceIndex


REPOSITORY_ROOT = Path(__file__).parents[1]
PILOT_BRIDGE_LAUNCHER = REPOSITORY_ROOT / "tools" / "sysml-pilot-bridge" / "run.py"


def test_bridge_launcher_reports_missing_pilot_build():
    environment = os.environ.copy()
    environment.pop("SYSML_PILOT_HOME", None)
    environment.pop("SYSML_PILOT_JAR", None)
    bridge_process = subprocess.run(
        [sys.executable, str(PILOT_BRIDGE_LAUNCHER), "parse", "."],
        input='{"files":[]}',
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )

    assert bridge_process.returncode == 2
    assert "Set SYSML_PILOT_HOME" in bridge_process.stderr


def pilot_jar_available() -> bool:
    configured_jar = os.environ.get("SYSML_PILOT_JAR")
    if configured_jar:
        return Path(configured_jar).is_file()
    pilot_home = os.environ.get("SYSML_PILOT_HOME")
    if not pilot_home:
        return False
    jar_directory = Path(pilot_home) / "org.omg.sysml.interactive" / "target"
    return any(jar_directory.glob("org.omg.sysml.interactive-*-all.jar"))


@pytest.mark.skipif(not pilot_jar_available(), reason="official Pilot fat JAR is not configured")
def test_included_bridge_parses_and_validates_workspace_with_official_pilot(monkeypatch):
    workspace_path = REPOSITORY_ROOT / "tests" / "fixtures" / "workspace"
    parser_inputs = [
        {"path": str(model_file.resolve()), "text": model_file.read_text(encoding="utf-8")}
        for model_file in sorted(workspace_path.rglob("*.sysml"))
    ]
    bridge_process = subprocess.run(
        [
            sys.executable,
            str(PILOT_BRIDGE_LAUNCHER),
            "parse",
            str(workspace_path),
        ],
        input=json.dumps({"files": parser_inputs}),
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
        timeout=120,
    )

    assert bridge_process.returncode == 0, bridge_process.stderr
    parser_response = json.loads(bridge_process.stdout)
    assert parser_response["parser"]["name"] == "SysML v2 Pilot Implementation"
    assert {"SysML 2.0", "KerML 1.0"} <= set(parser_response["parser"]["standards"])
    symbols = [
        symbol
        for parsed_file in parser_response["files"]
        for symbol in parsed_file["symbols"]
    ]
    symbol_names = {symbol["name"] for symbol in symbols}
    assert {"Vehicle", "Engine", "FuelPort", "Controller", "Idle", "Start", "R1"} <= symbol_names
    assert any(symbol["name"] == "Vehicle" and symbol["kind"] == "part_def" for symbol in symbols)
    assert any(symbol["name"] == "R1" and symbol["kind"] == "requirement_def" for symbol in symbols)
    assert any(
        reference["name"] == "Vehicle" and parsed_file["path"].endswith("links.sysml")
        for parsed_file in parser_response["files"]
        for reference in parsed_file["references"]
    )
    assert any(
        diagnostic["severity"] == "error" and parsed_file["path"].endswith("bad.sysml")
        for parsed_file in parser_response["files"]
        for diagnostic in parsed_file["diagnostics"]
    )

    monkeypatch.setenv(
        "SYSML_PILOT_RPC_COMMAND",
        shlex.join([sys.executable, str(PILOT_BRIDGE_LAUNCHER)]),
    )
    monkeypatch.delenv("SYSML_PILOT_COMMAND", raising=False)
    workspace_index = WorkspaceIndex(workspace_path, OfficialPilotAdapter())
    workspace_index.refresh()
    assert workspace_index.parser_info["name"] == "SysML v2 Pilot Implementation"
    assert workspace_index.definition("Vehicle")["kind"] == "part_def"
    assert any(
        diagnostic["file"].endswith("bad.sysml") and diagnostic["severity"] == "error"
        for diagnostic in workspace_index.diagnostics()
    )
