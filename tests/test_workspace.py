from pathlib import Path

from sysml_vim.workspace import WorkspaceIndex


def test_workspace_index_and_lookup():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()
    assert index.definition("Vehicle")
    refs = index.references("R1")
    assert any(r.get("relation") == "satisfy" for r in refs)


def test_workspace_diagnostics_include_unresolved_reference():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()
    diagnostics = index.diagnostics()
    assert any("Unresolved reference" in d["message"] for d in diagnostics)
