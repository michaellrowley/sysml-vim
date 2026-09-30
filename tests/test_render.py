from pathlib import Path
from types import SimpleNamespace

from sysml_vim.diagram import render_graph_data
from sysml_vim.model import Range, Reference
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
    assert "View Graph: composition (structural diagram)" in graph
    assert "«part def»" in graph
    assert "Vehicle" in graph
    assert "engine : Engine" in graph
    assert "wheel : Wheel" in graph
    assert "- Vehicle.engine -[typed_by]-> Engine" in graph


def test_dependency_view_includes_dependency_relationships():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()

    view = build_view(index, "dependencies")

    assert any(
        edge["source"] == "Fleet"
        and edge["target"] == "Vehicle"
        and edge["relation"] == "dependency"
        for edge in view["edges"]
    )


def test_graph_focused_on_view_renders_exposed_elements():
    file = "/workspace/model.sysml"
    symbols = [
        {
            "name": "DemoPkg",
            "kind": "package",
            "file": file,
            "range": {"line": 1, "col": 0, "end_col": 7},
            "container": None,
            "ancestors": [],
        },
        {
            "name": "rfTraceView",
            "kind": "view_usage",
            "file": file,
            "range": {"line": 2, "col": 7, "end_col": 18},
            "container": "DemoPkg",
            "ancestors": ["DemoPkg"],
        },
        {
            "name": "Vehicle",
            "kind": "part_def",
            "file": file,
            "range": {"line": 3, "col": 10, "end_col": 17},
            "container": "DemoPkg",
            "ancestors": ["DemoPkg"],
        },
        {
            "name": "engine",
            "kind": "part_usage",
            "file": file,
            "range": {"line": 4, "col": 8, "end_col": 14},
            "container": "Vehicle",
            "ancestors": ["DemoPkg", "Vehicle"],
        },
        {
            "name": "Engine",
            "kind": "part_def",
            "file": file,
            "range": {"line": 5, "col": 9, "end_col": 15},
            "container": "DemoPkg",
            "ancestors": ["DemoPkg"],
        },
        {
            "name": "RF1",
            "kind": "requirement_def",
            "file": file,
            "range": {"line": 6, "col": 14, "end_col": 17},
            "container": "DemoPkg",
            "ancestors": ["DemoPkg"],
        },
    ]
    references = [
        Reference(
            name="Vehicle",
            file=file,
            range=Range(line=2, col=30, end_col=37),
            relation="expose",
            source="rfTraceView",
        ),
        Reference(
            name="Engine",
            file=file,
            range=Range(line=4, col=17, end_col=23),
            relation="typed_by",
            source="engine",
        ),
        Reference(
            name="RF1",
            file=file,
            range=Range(line=2, col=40, end_col=43),
            relation="expose",
            source="rfTraceView",
        ),
        Reference(
            name="RF1",
            file=file,
            range=Range(line=3, col=20, end_col=23),
            relation="satisfy",
            source="Vehicle",
        ),
        Reference(
            name="Engine",
            file=file,
            range=Range(line=2, col=45, end_col=51),
            relation="expose",
            source="rfTraceView",
        ),
    ]
    index = SimpleNamespace(
        symbols=lambda: symbols,
        references_by_name={
            "Vehicle": [references[0]],
            "Engine": [references[1], references[4]],
            "RF1": [references[2], references[3]],
        },
    )

    view = build_view(index, "composition", focus="rfTraceView")
    graph = render_graph(view, focus="rfTraceView", depth=5)

    assert {symbol["name"] for symbol in view["nodes"]} == {
        "Vehicle",
        "engine",
        "Engine",
        "RF1",
    }
    assert all(symbol["name"] != "rfTraceView" for symbol in view["nodes"])
    assert any(edge["relation"] == "satisfy" for edge in view["edges"])
    assert "Vehicle" in graph
    assert "engine : Engine" in graph
    assert "- Vehicle.engine -[typed_by]-> Engine" in graph
    assert "- Vehicle -[satisfy]-> RF1" in graph


def test_graph_view_renders_exposed_parts_and_connection_ports():
    file = "/workspace/model.sysml"
    symbols = [
        {
            "name": "rfTraceView",
            "kind": "view_usage",
            "file": file,
            "range": {"line": 1, "col": 5, "end_col": 16},
            "container": "RF",
            "ancestors": ["RF"],
            "attributes": {
                "partType": "Generic::FullPartThread",
                "exposeTargets": (
                    "rfSensor,rfCoresetProcessor,DataLake,"
                    "rfSensorFeed,rfFeedForward"
                ),
            },
        },
        {
            "name": "FullPartThread",
            "kind": "view_def",
            "file": file,
            "range": {"line": 2, "col": 5, "end_col": 19},
            "container": "Generic",
            "ancestors": ["Generic"],
            "attributes": {
                "viewFilters": (
                    "@SysML::PartUsage,@SysML::PartDefinition,"
                    "@SysML::PortUsage,@SysML::PortDefinition,"
                    "@SysML::ConnectionUsage"
                )
            },
        },
        {
            "name": "rfSensor",
            "kind": "part_usage",
            "file": file,
            "range": {"line": 3, "col": 7, "end_col": 15},
            "container": "RF",
            "ancestors": ["RF"],
            "attributes": {"partType": "Generic::Sensor"},
        },
        {
            "name": "rfCoresetProcessor",
            "kind": "part_usage",
            "file": file,
            "range": {"line": 4, "col": 7, "end_col": 25},
            "container": "RF",
            "ancestors": ["RF"],
            "attributes": {"partType": "Generic::DataProcessingNode"},
        },
        {
            "name": "DataLake",
            "kind": "part_def",
            "file": file,
            "range": {"line": 5, "col": 12, "end_col": 20},
            "container": "Generic",
            "ancestors": ["Generic"],
            "attributes": {},
        },
        {
            "name": "Sensor",
            "kind": "part_def",
            "file": file,
            "range": {"line": 6, "col": 12, "end_col": 18},
            "container": "Generic",
            "ancestors": ["Generic"],
            "attributes": {},
        },
        {
            "name": "rawOutput",
            "kind": "port_usage",
            "file": file,
            "range": {"line": 7, "col": 9, "end_col": 18},
            "container": "Sensor",
            "ancestors": ["Generic", "Sensor"],
            "attributes": {"portType": "RawSensorDataPort"},
        },
        {
            "name": "UnfilteredAction",
            "kind": "action_usage",
            "file": file,
            "range": {"line": 8, "col": 10, "end_col": 25},
            "container": "Sensor",
            "ancestors": ["Generic", "Sensor"],
            "attributes": {},
        },
        {
            "name": "DataProcessingNode",
            "kind": "part_def",
            "file": file,
            "range": {"line": 9, "col": 12, "end_col": 30},
            "container": "Generic",
            "ancestors": ["Generic"],
            "attributes": {},
        },
        {
            "name": "rawInput",
            "kind": "port_usage",
            "file": file,
            "range": {"line": 10, "col": 9, "end_col": 17},
            "container": "DataProcessingNode",
            "ancestors": ["Generic", "DataProcessingNode"],
            "attributes": {"portType": "RawSensorDataPort"},
        },
        {
            "name": "processedOutput",
            "kind": "port_usage",
            "file": file,
            "range": {"line": 11, "col": 9, "end_col": 24},
            "container": "DataProcessingNode",
            "ancestors": ["Generic", "DataProcessingNode"],
            "attributes": {"portType": "ProcessedDataPort"},
        },
        {
            "name": "processedInput",
            "kind": "port_usage",
            "file": file,
            "range": {"line": 12, "col": 9, "end_col": 23},
            "container": "DataLake",
            "ancestors": ["Generic", "DataLake"],
            "attributes": {"portType": "ProcessedDataPort"},
        },
        {
            "name": "rfSensorFeed",
            "kind": "interface",
            "file": file,
            "range": {"line": 13, "col": 10, "end_col": 22},
            "container": "RF",
            "ancestors": ["RF"],
            "attributes": {},
        },
        {
            "name": "rfFeedForward",
            "kind": "interface",
            "file": file,
            "range": {"line": 14, "col": 10, "end_col": 23},
            "container": "RF",
            "ancestors": ["RF"],
            "attributes": {},
        },
    ]
    index = SimpleNamespace(
        symbols=lambda: symbols,
        references_by_name={},
        source_texts={
            file: (
                "interface rfSensorFeed connect\n"
                "    rfSensor.rawOutput to rfCoresetProcessor.rawInput;\n"
                "interface rfFeedForward connect\n"
                "    rfCoresetProcessor.processedOutput to DataLake.processedInput;\n"
            )
        },
    )

    view = build_view(index, "composition", focus="rfTraceView")
    rendered = render_graph_data(view, focus="rfTraceView", depth=5)
    graph = rendered["graph"]

    assert {symbol["name"] for symbol in view["nodes"]} == {
        "rfSensor",
        "rfCoresetProcessor",
        "DataLake",
        "rawOutput",
        "rawInput",
        "processedOutput",
        "processedInput",
    }
    assert any(
        edge["relation"] == "connect"
        and edge["source_feature"] == "rawOutput"
        and edge["target_feature"] == "rawInput"
        for edge in view["edges"]
    )
    assert "UnfilteredAction" not in graph
    assert "rfSensorFeed" in graph
    assert "rfFeedForward" in graph
    assert "- rfSensor.rawOutput -[rfSensorFeed]-> rfCoresetProcessor.rawInput" in graph
    assert "- rfCoresetProcessor.processedOutput -[rfFeedForward]-> DataLake.processedInput" in graph
    graph_nodes = {node["name"]: node for node in rendered["layout"]["nodes"]}
    assert set(graph_nodes) == {"rfSensor", "rfCoresetProcessor", "DataLake"}
    assert not {"Sensor", "DataProcessingNode"} & set(graph_nodes)
    assert graph_nodes["rfSensor"]["display_type"] == "Sensor"
    assert graph_nodes["rfCoresetProcessor"]["display_type"] == "DataProcessingNode"
    assert [
        feature["name"]
        for feature in graph_nodes["rfSensor"]["features"]
    ] == ["rawOutput"]
    assert "bdd [Package] RF [rfTraceView]" in graph
    assert {
        (edge["source"], edge["target"])
        for edge in rendered["layout"]["edges"]
    } == {
        ("rawOutput", "rawInput"),
        ("processedOutput", "processedInput"),
    }
