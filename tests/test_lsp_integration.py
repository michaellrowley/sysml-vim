from __future__ import annotations

import os
from pathlib import Path

import pytest

from sysml_vim.adapter import SysMLLspAdapter
from sysml_vim.workspace import WorkspaceIndex


CONFIGURED_SERVER = os.environ.get("SYSML_LSP_SERVER", "")
pytestmark = pytest.mark.skipif(
    not CONFIGURED_SERVER or not Path(CONFIGURED_SERVER).is_file(),
    reason="set SYSML_LSP_SERVER to run against the published SysML v2 LSP package",
)


def test_published_lsp_parses_models_and_reports_syntax_errors(tmp_path, monkeypatch):
    monkeypatch.delenv("SYSML_LSP_COMMAND", raising=False)
    package_file = tmp_path / "powertrain.sysml"
    package_file.write_text(
        """package Powertrain {
  part def Engine;
  part def Vehicle {
    part engine: Engine;
    attribute mass: Real;
  }
  requirement def SafeOperation;
  part def SafetyCase {
    satisfy requirement SafeOperation by self;
  }
}
""",
        encoding="utf-8",
    )
    importing_file = tmp_path / "fleet.sysml"
    importing_file.write_text(
        """package FleetModel {
  private import Powertrain::Vehicle;
  part def Fleet {
    part lead: Vehicle;
  }
}
""",
        encoding="utf-8",
    )
    malformed_file = tmp_path / "broken.sysml"
    malformed_file.write_text(
        "package Broken {\n  part def Incomplete {\n",
        encoding="utf-8",
    )

    adapter = SysMLLspAdapter()
    try:
        index = WorkspaceIndex(tmp_path, adapter)
        index.refresh()

        symbols_by_name = {symbol["name"]: symbol for symbol in index.symbols()}
        assert symbols_by_name["Engine"]["kind"] == "part_def"
        assert symbols_by_name["Vehicle"]["kind"] == "part_def"
        assert symbols_by_name["engine"]["kind"] == "part_usage"
        assert symbols_by_name["mass"]["kind"] == "attribute_usage"
        assert symbols_by_name["SafetyCase"]["kind"] == "part_def"
        error_files = {
            Path(diagnostic["file"]).name
            for diagnostic in index.diagnostics()
            if diagnostic["severity"] == "error"
        }
        assert error_files == {"broken.sysml"}
        assert any(
            reference["relation"] == "typed_by"
            for reference in index.references("Vehicle")
        )
        assert index.parser_info["name"] == "SysML v2 Language Server (ANTLR)"
        assert index.parser_info["version"] != "unknown"

        package_file.write_text(
            package_file.read_text(encoding="utf-8").replace(
                "attribute mass: Real;",
                "attribute mass: Real;\n    attribute ratedPower: Real;",
            ),
            encoding="utf-8",
        )
        assert index.is_current() is False
        index.refresh()
        assert index.definition("ratedPower")["kind"] == "attribute_usage"
    finally:
        adapter.close()
