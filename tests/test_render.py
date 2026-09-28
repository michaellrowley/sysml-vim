from pathlib import Path

from sysml_vim.render import build_view, render_dot, render_graph, render_text
from sysml_vim.workspace import WorkspaceIndex


def test_render_text_and_dot():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()
    view = build_view(index, "composition")
    text = render_text(view)
    dot = render_dot(view)
    assert "View: composition" in text
    assert "digraph" in dot


def test_render_graph_hierarchy():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()
    view = build_view(index, "composition", focus="Vehicle")
    graph = render_graph(view, focus="Vehicle", depth=5)
    assert "View Graph: composition (ELK-style layered blocks)" in graph
    assert "Bright junctions mark shared routes" in graph
    assert "Vehicle:part_def" in graph
    assert "- Vehicle -[contains]-> engine" in graph or "- Vehicle -[contains]-> wheel" in graph
    assert "- engine -[typed_by]-> Engine" in graph


def test_dependency_view_includes_dependency_relationships():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()

    view = build_view(index, "dependencies")

    assert {
        "source": "Fleet",
        "target": "Vehicle",
        "relation": "dependency",
    } in view["edges"]
