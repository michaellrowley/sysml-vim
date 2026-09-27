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


def test_workspace_import_and_behavior_references():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()

    vehicle_refs = index.references("Vehicle")
    assert any(r.get("relation") == "import" for r in vehicle_refs)
    assert any(r.get("relation") == "allocate" for r in vehicle_refs)

    state_refs = index.references("Active")
    assert any(r.get("relation") == "transition" for r in state_refs)
