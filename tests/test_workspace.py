from pathlib import Path

from sysml_vim.workspace import WorkspaceIndex


def test_workspace_index_and_lookup():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()
    assert index.definition("Vehicle")
    refs = index.references("R1")
    assert any(r.get("relation") == "satisfy" for r in refs)


def test_workspace_diagnostics_include_official_parser_errors():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()
    diagnostics = index.diagnostics()
    assert any(
        d["file"].endswith("bad.sysml") and d["severity"] == "error"
        for d in diagnostics
    )


def test_workspace_import_and_behavior_references():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()

    vehicle_refs = index.references("Vehicle")
    assert any(r.get("relation") == "import" for r in vehicle_refs)
    assert any(r.get("relation") == "allocate" for r in vehicle_refs)
    assert any(r.get("relation") == "dependency" for r in vehicle_refs)
    assert index.definition("Active")["kind"] == "state_def"


def test_workspace_snapshot_detects_model_file_changes(tmp_path):
    class CountingParser:
        calls = 0

        def parse_workspace(self, workspace, files):
            self.calls += 1
            return {
                "parser": {
                    "name": "SysML v2 Language Server (ANTLR)",
                    "version": "0.31.0",
                    "standards": [
                        "SysML v2 textual grammar derived from OMG KEBNF",
                        "KerML textual grammar derived from OMG KEBNF",
                    ],
                },
                "files": [
                    {
                        "path": source["path"],
                        "symbols": [],
                        "references": [],
                        "diagnostics": [],
                        "imports": [],
                    }
                    for source in files
                ],
            }

    model_file = tmp_path / "model.sysml"
    model_file.write_text("package First;")
    parser_adapter = CountingParser()
    index = WorkspaceIndex(model_file.parent, parser_adapter)

    index.refresh()
    assert index.is_current() is True
    assert parser_adapter.calls == 1

    model_file.write_text("package ChangedName;")
    assert index.is_current() is False
    index.refresh()
    assert parser_adapter.calls == 2


def test_workspace_indexes_unsaved_and_new_document_overrides(tmp_path):
    class CapturingParser:
        parsed_files = []

        def parse_workspace(self, workspace, files):
            self.parsed_files = list(files)
            return {
                "parser": {
                    "name": "SysML v2 Language Server (ANTLR)",
                    "version": "0.31.0",
                    "standards": [
                        "SysML v2 textual grammar derived from OMG KEBNF",
                        "KerML textual grammar derived from OMG KEBNF",
                    ],
                },
                "files": [
                    {
                        "path": source["path"],
                        "symbols": [],
                        "references": [],
                        "diagnostics": [],
                        "imports": [],
                    }
                    for source in files
                ],
            }

    existing_file = tmp_path / "model.sysml"
    existing_file.write_text("package Saved;")
    new_file = tmp_path / "draft.sysml"
    source_overrides = {
        str(existing_file): "package Unsaved;",
        str(new_file): "package Draft;",
    }
    parser_adapter = CapturingParser()
    index = WorkspaceIndex(tmp_path, parser_adapter)

    index.refresh(source_overrides)

    parsed_text_by_path = {
        source["path"]: source["text"]
        for source in parser_adapter.parsed_files
    }
    assert parsed_text_by_path[str(existing_file.resolve())] == "package Unsaved;"
    assert parsed_text_by_path[str(new_file.resolve())] == "package Draft;"
    assert existing_file.read_text() == "package Saved;"
    assert index.is_current(source_overrides) is True
    assert index.is_current() is False
