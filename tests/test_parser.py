from pathlib import Path

import pytest

from sysml_vim.adapter import ParserBackendError
from sysml_vim.workspace import WorkspaceIndex


def test_lsp_model_projection_indexes_representative_sysml_constructs():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()

    symbols_by_name = {symbol["name"]: symbol for symbol in index.symbols()}
    assert symbols_by_name["Ygkahzr"]["kind"] == "part_def"
    assert symbols_by_name["hxipof"]["kind"] == "part_usage"
    assert symbols_by_name["Sr"]["kind"] == "requirement_def"
    assert symbols_by_name["Fdopfyfvfw"]["kind"] == "part_def"
    assert symbols_by_name["Vter"]["kind"] == "state_def"
    assert symbols_by_name["Thhat"]["kind"] == "action_def"

    reference_relations = {
        reference["relation"] for reference in index.references("Ygkahzr")
    }
    assert {"import", "allocate", "dependency"} <= reference_relations
    assert any(reference["relation"] == "satisfy" for reference in index.references("Sr"))


def test_language_server_diagnostics_are_preserved():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()

    diagnostics = index.diagnostics()
    assert any(
        diagnostic["file"].endswith("bad.sysml")
        and diagnostic["severity"] == "error"
        and diagnostic["source"] == "sysml-v2-lsp"
        for diagnostic in diagnostics
    )


def test_parser_response_must_identify_standards_and_cover_requested_files():
    class InvalidParser:
        def parse_workspace(self, workspace, files):
            return {"parser": {"name": "unknown", "version": "1"}, "files": []}

    with pytest.raises(ParserBackendError, match="SysML v2 LSP"):
        WorkspaceIndex(Path("tests/fixtures/workspace"), InvalidParser()).refresh()
