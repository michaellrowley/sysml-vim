from pathlib import Path

import pytest

from sysml_vim.adapter import ParserBackendError
from sysml_vim.workspace import WorkspaceIndex


def test_official_parser_output_indexes_representative_sysml_constructs():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()

    symbols_by_name = {symbol["name"]: symbol for symbol in index.symbols()}
    assert symbols_by_name["Vehicle"]["kind"] == "part_def"
    assert symbols_by_name["engine"]["kind"] == "part_usage"
    assert symbols_by_name["R1"]["kind"] == "requirement_def"
    assert symbols_by_name["Controller"]["kind"] == "part_def"
    assert symbols_by_name["Idle"]["kind"] == "state_def"
    assert symbols_by_name["Start"]["kind"] == "action_def"

    reference_relations = {
        reference["relation"] for reference in index.references("Vehicle")
    }
    assert {"import", "allocate", "trace"} <= reference_relations
    assert any(reference["relation"] == "transition" for reference in index.references("Active"))
    assert any(reference["relation"] == "satisfy" for reference in index.references("R1"))


def test_parser_diagnostics_are_preserved():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()

    diagnostics = index.diagnostics()
    assert any(
        diagnostic["file"].endswith("bad.sysml")
        and diagnostic["severity"] == "error"
        and diagnostic["source"] == "SysML v2 Pilot Implementation"
        for diagnostic in diagnostics
    )


def test_parser_response_must_identify_standards_and_cover_requested_files():
    class InvalidParser:
        def parse_workspace(self, workspace, files):
            return {"parser": {"name": "unknown", "version": "1"}, "files": []}

    with pytest.raises(ParserBackendError, match="SysML v2 Pilot"):
        WorkspaceIndex(Path("tests/fixtures/workspace"), InvalidParser()).refresh()
