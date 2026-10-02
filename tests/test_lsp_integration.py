from __future__ import annotations

import os
from pathlib import Path

import pytest

from sysml_vim.adapter import SysMLLspAdapter
from sysml_vim.workspace import WorkspaceIndex


CONFIGURED_SERVER = os.environ.get("SYSML_LSP_SERVER", "")
pytestmark = pytest.mark.skipif(
    not CONFIGURED_SERVER or not Path(CONFIGURED_SERVER).is_file(),
    reason="set SYSML_LSP_SERVER to run against the configured SysML v2 LSP package",
)


def test_published_lsp_parses_models_and_reports_syntax_errors(tmp_path, monkeypatch):
    monkeypatch.delenv("SYSML_LSP_COMMAND", raising=False)
    package_file = tmp_path / "powertrain.sysml"
    package_file.write_text(
        """package Boyhhrbqyz {
  part def Tegyxc;
  part def Ygkahzr {
    part hxipof: Tegyxc;
    attribute lmqw: Real;
  }
  requirement def Xbomsupddvpmf;
  part def Nwfuxqjbpo {
    satisfy requirement Xbomsupddvpmf by self;
  }
}
""",
        encoding="utf-8",
    )
    importing_file = tmp_path / "fleet.sysml"
    importing_file.write_text(
        """package Awshovsqoe {
  private import Boyhhrbqyz::Ygkahzr;
  part def Pxish {
    part hcgg: Ygkahzr;
  }
}
""",
        encoding="utf-8",
    )
    malformed_file = tmp_path / "broken.sysml"
    malformed_file.write_text(
        "package Umgluz {\n  part def Syuceouopq {\n",
        encoding="utf-8",
    )

    adapter = SysMLLspAdapter()
    try:
        index = WorkspaceIndex(tmp_path, adapter)
        index.refresh()

        symbols_by_name = {symbol["name"]: symbol for symbol in index.symbols()}
        assert symbols_by_name["Tegyxc"]["kind"] == "part_def"
        assert symbols_by_name["Ygkahzr"]["kind"] == "part_def"
        assert symbols_by_name["hxipof"]["kind"] == "part_usage"
        assert symbols_by_name["lmqw"]["kind"] == "attribute_usage"
        assert symbols_by_name["Nwfuxqjbpo"]["kind"] == "part_def"
        error_files = {
            Path(diagnostic["file"]).name
            for diagnostic in index.diagnostics()
            if diagnostic["severity"] == "error"
        }
        assert error_files == {"broken.sysml"}
        assert any(
            reference["relation"] == "typed_by"
            for reference in index.references("Ygkahzr")
        )
        assert index.parser_info["name"] == "SysML v2 Language Server (ANTLR)"
        assert index.parser_info["version"] != "unknown"

        unsaved_text = package_file.read_text(encoding="utf-8").replace(
            "  requirement def Xbomsupddvpmf;",
            "  part def Lpirvregvvlo;\n  requirement def Xbomsupddvpmf;",
        )
        document_overrides = {str(package_file.resolve()): unsaved_text}
        index.refresh(document_overrides)
        assert index.definition("Lpirvregvvlo")["kind"] == "part_def"
        assert "Lpirvregvvlo" not in package_file.read_text(encoding="utf-8")
        assert index.is_current(document_overrides) is True
        assert index.is_current() is False
        index.refresh()
        assert index.definition("Lpirvregvvlo") is None

        package_file.write_text(
            package_file.read_text(encoding="utf-8").replace(
                "attribute lmqw: Real;",
                "attribute lmqw: Real;\n    attribute gbskygodlk: Real;",
            ),
            encoding="utf-8",
        )
        assert index.is_current() is False
        index.refresh()
        assert index.definition("gbskygodlk")["kind"] == "attribute_usage"
    finally:
        adapter.close()


def test_configured_lsp_projects_item_flow_payload_and_endpoints(
    tmp_path,
    monkeypatch,
):
    monkeypatch.delenv("SYSML_LSP_COMMAND", raising=False)
    model_file = tmp_path / "flow.sysml"
    model_file.write_text(
        """package FlowFixture {
  item def Payload;
  part source {
    item payloadOut : Payload;
  }
  part target {
    item payloadIn : Payload;
  }
  interface def Link {
    flow of Payload from source.payloadOut to target.payloadIn;
  }
}
""",
        encoding="utf-8",
    )

    adapter = SysMLLspAdapter()
    try:
        index = WorkspaceIndex(tmp_path, adapter)
        index.refresh()

        flow_symbols = [
            symbol
            for symbol in index.symbols()
            if "flow" in symbol["kind"].lower()
        ]
        assert len(flow_symbols) == 1
        attributes = flow_symbols[0]["attributes"]
        assert attributes["itemType"] == "Payload"
        assert attributes["flowSource"] == "source.payloadOut"
        assert attributes["flowTarget"] == "target.payloadIn"
    finally:
        adapter.close()
