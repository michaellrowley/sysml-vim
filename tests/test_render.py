from pathlib import Path
from types import SimpleNamespace

import pytest

import sysml_vim.render as render_module
from sysml_vim.diagram import _display_width, render_graph_data
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
    view = build_view(index, "composition", focus="Ygkahzr")
    graph = render_graph(view, focus="Ygkahzr", depth=5)
    assert "View Graph: composition (structural diagram)" in graph
    assert "«part def»" in graph
    assert "Ygkahzr" in graph
    assert "hxipof : Tegyxc" in graph
    assert "fpzwr : Moech" in graph
    assert "- Ygkahzr.hxipof -[typed_by]-> Tegyxc" in graph


def test_dependency_view_includes_dependency_relationships():
    index = WorkspaceIndex(Path("tests/fixtures/workspace"))
    index.refresh()

    view = build_view(index, "dependencies")

    assert any(
        edge["source"] == "Pxish"
        and edge["target"] == "Ygkahzr"
        and edge["relation"] == "dependency"
        for edge in view["edges"]
    )


def test_graph_focused_on_view_renders_exposed_elements():
    file = "/workspace/model.sysml"
    symbols = [
        {
            "name": "Drkxmyd",
            "kind": "package",
            "file": file,
            "range": {"line": 1, "col": 0, "end_col": 7},
            "container": None,
            "ancestors": [],
        },
        {
            "name": "kmvyewcivjd",
            "kind": "view_usage",
            "file": file,
            "range": {"line": 2, "col": 7, "end_col": 18},
            "container": "Drkxmyd",
            "ancestors": ["Drkxmyd"],
        },
        {
            "name": "Ygkahzr",
            "kind": "part_def",
            "file": file,
            "range": {"line": 3, "col": 10, "end_col": 17},
            "container": "Drkxmyd",
            "ancestors": ["Drkxmyd"],
        },
        {
            "name": "hxipof",
            "kind": "part_usage",
            "file": file,
            "range": {"line": 4, "col": 8, "end_col": 14},
            "container": "Ygkahzr",
            "ancestors": ["Drkxmyd", "Ygkahzr"],
        },
        {
            "name": "Tegyxc",
            "kind": "part_def",
            "file": file,
            "range": {"line": 5, "col": 9, "end_col": 15},
            "container": "Drkxmyd",
            "ancestors": ["Drkxmyd"],
        },
        {
            "name": "Pda",
            "kind": "requirement_def",
            "file": file,
            "range": {"line": 6, "col": 14, "end_col": 17},
            "container": "Drkxmyd",
            "ancestors": ["Drkxmyd"],
        },
    ]
    references = [
        Reference(
            name="Ygkahzr",
            file=file,
            range=Range(line=2, col=30, end_col=37),
            relation="expose",
            source="kmvyewcivjd",
        ),
        Reference(
            name="Tegyxc",
            file=file,
            range=Range(line=4, col=17, end_col=23),
            relation="typed_by",
            source="hxipof",
        ),
        Reference(
            name="Pda",
            file=file,
            range=Range(line=2, col=40, end_col=43),
            relation="expose",
            source="kmvyewcivjd",
        ),
        Reference(
            name="Pda",
            file=file,
            range=Range(line=3, col=20, end_col=23),
            relation="satisfy",
            source="Ygkahzr",
        ),
        Reference(
            name="Tegyxc",
            file=file,
            range=Range(line=2, col=45, end_col=51),
            relation="expose",
            source="kmvyewcivjd",
        ),
    ]
    index = SimpleNamespace(
        symbols=lambda: symbols,
        references_by_name={
            "Ygkahzr": [references[0]],
            "Tegyxc": [references[1], references[4]],
            "Pda": [references[2], references[3]],
        },
    )

    view = build_view(index, "composition", focus="kmvyewcivjd")
    graph = render_graph(view, focus="kmvyewcivjd", depth=5)

    assert {symbol["name"] for symbol in view["nodes"]} == {
        "Ygkahzr",
        "hxipof",
        "Tegyxc",
        "Pda",
    }
    assert all(symbol["name"] != "kmvyewcivjd" for symbol in view["nodes"])
    assert any(edge["relation"] == "satisfy" for edge in view["edges"])
    assert "Ygkahzr" in graph
    assert "hxipof : Tegyxc" in graph
    assert "- Ygkahzr.hxipof -[typed_by]-> Tegyxc" in graph
    assert "- Ygkahzr -[satisfy]-> Pda" in graph


def test_graph_view_renders_exposed_parts_and_connection_ports():
    file = "/workspace/model.sysml"
    symbols = [
        {
            "name": "kmvyewcivjd",
            "kind": "view_usage",
            "file": file,
            "range": {"line": 1, "col": 5, "end_col": 16},
            "container": "RF",
            "ancestors": ["RF"],
            "attributes": {
                "partType": "Kjeodcj::Jvvvxsoqeiebml",
                "exposeTargets": (
                    "hxpfgclq,glrlvstlbuktcsrjij,Pllnafzk,"
                    "bsqfvnqwbtxt,wmwpfkemwhaes"
                ),
            },
        },
        {
            "name": "Jvvvxsoqeiebml",
            "kind": "view_def",
            "file": file,
            "range": {"line": 2, "col": 5, "end_col": 19},
            "container": "Kjeodcj",
            "ancestors": ["Kjeodcj"],
            "attributes": {
                "viewFilters": (
                    "@SysML::PartUsage,@SysML::PartDefinition,"
                    "@SysML::PortUsage,@SysML::PortDefinition,"
                    "@SysML::ConnectionUsage"
                )
            },
        },
        {
            "name": "hxpfgclq",
            "kind": "part_usage",
            "file": file,
            "range": {"line": 3, "col": 7, "end_col": 15},
            "container": "RF",
            "ancestors": ["RF"],
            "attributes": {"partType": "Kjeodcj::Jzoufc"},
        },
        {
            "name": "glrlvstlbuktcsrjij",
            "kind": "part_usage",
            "file": file,
            "range": {"line": 4, "col": 7, "end_col": 25},
            "container": "RF",
            "ancestors": ["RF"],
            "attributes": {"partType": "Kjeodcj::Trhembbddohlkzteve"},
        },
        {
            "name": "Pllnafzk",
            "kind": "part_def",
            "file": file,
            "range": {"line": 5, "col": 12, "end_col": 20},
            "container": "Kjeodcj",
            "ancestors": ["Kjeodcj"],
            "attributes": {},
        },
        {
            "name": "Jzoufc",
            "kind": "part_def",
            "file": file,
            "range": {"line": 6, "col": 12, "end_col": 18},
            "container": "Kjeodcj",
            "ancestors": ["Kjeodcj"],
            "attributes": {},
        },
        {
            "name": "wifodicrm",
            "kind": "port_usage",
            "file": file,
            "range": {"line": 7, "col": 9, "end_col": 18},
            "container": "Jzoufc",
            "ancestors": ["Kjeodcj", "Jzoufc"],
            "attributes": {"portType": "RawSensorDataPort"},
        },
        {
            "name": "Rzlhjvapyihbramu",
            "kind": "action_usage",
            "file": file,
            "range": {"line": 8, "col": 10, "end_col": 25},
            "container": "Jzoufc",
            "ancestors": ["Kjeodcj", "Jzoufc"],
            "attributes": {},
        },
        {
            "name": "Trhembbddohlkzteve",
            "kind": "part_def",
            "file": file,
            "range": {"line": 9, "col": 12, "end_col": 30},
            "container": "Kjeodcj",
            "ancestors": ["Kjeodcj"],
            "attributes": {},
        },
        {
            "name": "akehojnq",
            "kind": "port_usage",
            "file": file,
            "range": {"line": 10, "col": 9, "end_col": 17},
            "container": "Trhembbddohlkzteve",
            "ancestors": ["Kjeodcj", "Trhembbddohlkzteve"],
            "attributes": {"portType": "RawSensorDataPort"},
        },
        {
            "name": "yoksvbkshnusqpk",
            "kind": "port_usage",
            "file": file,
            "range": {"line": 11, "col": 9, "end_col": 24},
            "container": "Trhembbddohlkzteve",
            "ancestors": ["Kjeodcj", "Trhembbddohlkzteve"],
            "attributes": {"portType": "ProcessedDataPort"},
        },
        {
            "name": "pxceeudjxhqkyw",
            "kind": "port_usage",
            "file": file,
            "range": {"line": 12, "col": 9, "end_col": 23},
            "container": "Pllnafzk",
            "ancestors": ["Kjeodcj", "Pllnafzk"],
            "attributes": {"portType": "ProcessedDataPort"},
        },
        {
            "name": "bsqfvnqwbtxt",
            "kind": "interface",
            "file": file,
            "range": {"line": 1, "col": 10, "end_col": 22},
            "container": "RF",
            "ancestors": ["RF"],
            "attributes": {},
        },
        {
            "name": "wmwpfkemwhaes",
            "kind": "interface",
            "file": file,
            "range": {"line": 3, "col": 10, "end_col": 23},
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
                "interface bsqfvnqwbtxt connect\n"
                "    hxpfgclq.wifodicrm to glrlvstlbuktcsrjij.akehojnq;\n"
                "interface wmwpfkemwhaes connect\n"
                "    glrlvstlbuktcsrjij.yoksvbkshnusqpk to Pllnafzk.pxceeudjxhqkyw;\n"
            )
        },
    )

    view = build_view(index, "composition", focus="kmvyewcivjd")
    rendered = render_graph_data(view, focus="kmvyewcivjd", depth=5)
    graph = rendered["graph"]

    assert {symbol["name"] for symbol in view["nodes"]} == {
        "hxpfgclq",
        "glrlvstlbuktcsrjij",
        "Pllnafzk",
        "wifodicrm",
        "akehojnq",
        "yoksvbkshnusqpk",
        "pxceeudjxhqkyw",
    }
    assert any(
        edge["relation"] == "connect"
        and edge["source_feature"] == "wifodicrm"
        and edge["target_feature"] == "akehojnq"
        for edge in view["edges"]
    )
    assert "Rzlhjvapyihbramu" not in graph
    assert "bsqfvnqwbtxt" in graph
    assert "wmwpfkemwhaes" in graph
    assert "- hxpfgclq.wifodicrm -[bsqfvnqwbtxt]-> glrlvstlbuktcsrjij.akehojnq" in graph
    assert "- glrlvstlbuktcsrjij.yoksvbkshnusqpk -[wmwpfkemwhaes]-> Pllnafzk.pxceeudjxhqkyw" in graph
    graph_nodes = {node["name"]: node for node in rendered["layout"]["nodes"]}
    assert set(graph_nodes) == {"hxpfgclq", "glrlvstlbuktcsrjij", "Pllnafzk"}
    assert not {"Jzoufc", "Trhembbddohlkzteve"} & set(graph_nodes)
    assert graph_nodes["hxpfgclq"]["display_type"] == "Jzoufc"
    assert graph_nodes["glrlvstlbuktcsrjij"]["display_type"] == "Trhembbddohlkzteve"
    assert [
        feature["name"]
        for feature in graph_nodes["hxpfgclq"]["features"]
    ] == ["wifodicrm"]
    assert "bdd [Package] RF [kmvyewcivjd]" in graph
    assert {
        (edge["source"], edge["target"])
        for edge in rendered["layout"]["edges"]
    } == {
        ("wifodicrm", "akehojnq"),
        ("yoksvbkshnusqpk", "pxceeudjxhqkyw"),
    }


def test_graph_view_expands_recursive_exposure_and_typed_connections():
    file = "/workspace/model.sysml"

    def symbol(
        name,
        kind,
        container,
        ancestors,
        attributes=None,
        *,
        line,
    ):
        return {
            "name": name,
            "kind": kind,
            "file": file,
            "range": {"line": line, "col": 0, "end_col": len(name)},
            "container": container,
            "ancestors": ancestors,
            "attributes": attributes or {},
        }

    symbols = [
        symbol(
            "nlucolsgtwqt",
            "view_usage",
            "Ezi",
            ["Tgpsspercssvuy", "Ezi"],
            {
                "partType": "Kjeodcj::Rwdkxfzclmck::Jvvvxsoqeiebml",
                "exposeTargets": "sharedDataLake,Ezi::**",
            },
            line=1,
        ),
        symbol(
            "Jvvvxsoqeiebml",
            "view_def",
            "Rwdkxfzclmck",
            ["Kjeodcj", "Rwdkxfzclmck"],
            {
                "viewFilters": (
                    "@SysML::PartUsage,@SysML::PartDefinition,"
                    "@SysML::PortUsage,@SysML::PortDefinition,"
                    "@SysML::ItemUsage,@SysML::ConnectionUsage"
                )
            },
            line=2,
        ),
        symbol("Ezi", "package", "Tgpsspercssvuy", ["Tgpsspercssvuy"], line=3),
        symbol("Iekznjnajw", "package", "Ezi", ["Tgpsspercssvuy", "Ezi"], line=4),
        symbol(
            "cfpymrhtf",
            "part_usage",
            "Ezi",
            ["Tgpsspercssvuy", "Ezi"],
            {"partType": "Jzoufc"},
            line=5,
        ),
        symbol(
            "cyvkldknwsjx",
            "part_usage",
            "Ezi",
            ["Tgpsspercssvuy", "Ezi"],
            {"partType": "Trhembbddohlkzteve"},
            line=6,
        ),
        symbol(
            "wifodicrm",
            "port_usage",
            "cfpymrhtf",
            ["Tgpsspercssvuy", "Ezi", "cfpymrhtf"],
            {"portType": "Aiqqbktnbypikb"},
            line=13,
        ),
        symbol(
            "akehojnq",
            "port_usage",
            "cyvkldknwsjx",
            ["Tgpsspercssvuy", "Ezi", "cyvkldknwsjx"],
            {"portType": "Aiqqbktnbypikb"},
            line=14,
        ),
        symbol(
            "yoksvbkshnusqpk",
            "port_usage",
            "cyvkldknwsjx",
            ["Tgpsspercssvuy", "Ezi", "cyvkldknwsjx"],
            {"portType": "Tcshmldglszqvucl"},
            line=15,
        ),
        symbol(
            "akajwvdiqdyzs",
            "interface",
            "Ezi",
            ["Tgpsspercssvuy", "Ezi"],
            line=6,
        ),
        symbol(
            "bcgrftvxyrbllgvqwxitgxspz",
            "interface",
            "Ezi",
            ["Tgpsspercssvuy", "Ezi"],
            line=8,
        ),
        symbol(
            "earcwqymvk",
            "port_usage",
            "Iekznjnajw",
            ["Tgpsspercssvuy", "Ezi", "Iekznjnajw"],
            {"portType": "Aiqqbktnbypikb"},
            line=9,
        ),
        symbol(
            "jztgzdthajenn",
            "action_usage",
            "Ezi",
            ["Tgpsspercssvuy", "Ezi"],
            line=10,
        ),
        symbol(
            "cfpymrhtf",
            "part_usage",
            "Kcrls",
            ["Tgpsspercssvuy", "Kcrls"],
            {"partType": "UnrelatedSensor"},
            line=11,
        ),
        symbol(
            "Kcrls",
            "package",
            "Tgpsspercssvuy",
            ["Tgpsspercssvuy"],
            line=17,
        ),
        symbol(
            "akajwvdiqdyzs",
            "interface",
            "Kcrls",
            ["Tgpsspercssvuy", "Kcrls"],
            line=18,
        ),
        symbol(
            "sharedDataLake",
            "part_usage",
            "Hygjevuvrxwq",
            ["Eigpwxvv", "Hygjevuvrxwq"],
            {"partType": "Pllnafzk"},
            line=12,
        ),
        symbol(
            "pxceeudjxhqkyw",
            "port_usage",
            "sharedDataLake",
            ["Eigpwxvv", "Hygjevuvrxwq", "sharedDataLake"],
            {"portType": "Tcshmldglszqvucl"},
            line=16,
        ),
    ]
    index = SimpleNamespace(
        symbols=lambda: symbols,
        references_by_name={},
        source_texts={
            file: (
                "package Kcrls {\n"
                "    interface akajwvdiqdyzs connect\n"
                "        fnrcwcpr.wifodicrm to ukmfj.akehojnq;\n"
                "}\n"
                "package Ezi {\n"
                "    interface akajwvdiqdyzs : Svgjzwsvnajof\n"
                "        connect cfpymrhtf.wifodicrm to cyvkldknwsjx.akehojnq;\n"
                "    interface bcgrftvxyrbllgvqwxitgxspz : Dskoderbwoqqulkm connect\n"
                "        cyvkldknwsjx.yoksvbkshnusqpk to sharedDataLake.pxceeudjxhqkyw;\n"
                "}\n"
            )
        },
    )

    view = build_view(index, "composition", focus="nlucolsgtwqt")
    rendered = render_graph_data(view, focus="nlucolsgtwqt", depth=5)

    visible_members = [
        (item["name"], item["container"])
        for item in view["nodes"]
    ]
    assert ("cfpymrhtf", "Ezi") in visible_members
    assert ("cyvkldknwsjx", "Ezi") in visible_members
    assert ("earcwqymvk", "Iekznjnajw") in visible_members
    assert ("sharedDataLake", "Hygjevuvrxwq") in visible_members
    assert ("cfpymrhtf", "Kcrls") not in visible_members
    assert all(name != "jztgzdthajenn" for name, _ in visible_members)
    assert "- cfpymrhtf.wifodicrm -[akajwvdiqdyzs]-> cyvkldknwsjx.akehojnq" in rendered["graph"]
    assert (
        "- cyvkldknwsjx.yoksvbkshnusqpk -[bcgrftvxyrbllgvqwxitgxspz]-> "
        "sharedDataLake.pxceeudjxhqkyw"
    ) in rendered["graph"]


def _standard_view_index(view_definition, *, specialized=False):
    file = "/workspace/model.sysml"

    def symbol(
        name,
        kind,
        line,
        *,
        container=None,
        ancestors=(),
        attributes=None,
    ):
        return {
            "name": name,
            "kind": kind,
            "file": file,
            "range": {"line": line, "col": 0, "end_col": len(name)},
            "container": container,
            "ancestors": list(ancestors),
            "attributes": attributes or {},
        }

    concrete_view_type = "CustomInterconnectionView" if specialized else view_definition
    view_attributes = {
        "partType": f"StandardViewDefinitions::{concrete_view_type}",
        "exposeTargets": "Alpha,Beta,ifConnect",
    }
    symbols = [
        symbol(
            "bleTraceView",
            "view_usage",
            1,
            container="System",
            ancestors=("System",),
            attributes=view_attributes,
        ),
        symbol("Alpha", "part_usage", 2, container="System", ancestors=("System",), attributes={"partType": "Pump"}),
        symbol("Beta", "part_usage", 3, container="System", ancestors=("System",), attributes={"partType": "Valve"}),
        symbol(
            "outlet",
            "port_usage",
            4,
            container="Alpha",
            ancestors=("System", "Alpha"),
            attributes={"portType": "DataPort"},
        ),
        symbol(
            "inlet",
            "port_usage",
            5,
            container="Beta",
            ancestors=("System", "Beta"),
            attributes={"portType": "DataPort"},
        ),
        symbol("WorkA", "action_usage", 6, container="Alpha", ancestors=("System", "Alpha")),
        symbol("WorkB", "action_usage", 7, container="Beta", ancestors=("System", "Beta")),
        symbol("Ready", "state_usage", 8, container="Alpha", ancestors=("System", "Alpha")),
        symbol("Done", "state_usage", 9, container="Alpha", ancestors=("System", "Alpha")),
        symbol(
            "ifConnect",
            "interface",
            4,
            container="System",
            ancestors=("System",),
        ),
        symbol(
            "DataPort",
            "port_def",
            11,
            container="System",
            ancestors=("System",),
        ),
    ]
    if specialized:
        symbols.append(
            symbol(
                "CustomInterconnectionView",
                "view_def",
                12,
                container="System",
                ancestors=("System",),
                attributes={
                    "viewFilters": (
                        "@SysML::PartUsage,@SysML::PortUsage,"
                        "@SysML::ConnectionUsage"
                    )
                },
            )
        )
    references = [
        Reference(
            name="InterconnectionView",
            file=file,
            range=Range(12, 0, 1),
            relation="specializes",
            source="CustomInterconnectionView",
        )
    ] if specialized else []
    return SimpleNamespace(
        symbols=lambda: symbols,
        references_by_name={
            reference.name: [reference] for reference in references
        },
        source_texts={
            file: (
                "view bleTraceView;\n"
                "part Alpha;\n"
                "part Beta;\n"
                "interface ifConnect connect\n"
                "    Alpha.outlet to Beta.inlet;\n"
            )
        },
    )


@pytest.mark.parametrize(
    ("view_definition", "presentation"),
    [
        ("GeneralView", "general"),
        ("InterconnectionView", "interconnection"),
        ("ActionFlowView", "action_flow"),
        ("StateTransitionView", "state_transition"),
        ("SequenceView", "sequence"),
        ("GeometryView", "geometry"),
        ("GridView", "grid"),
        ("BrowserView", "browser"),
    ],
)
def test_standard_view_definitions_select_a_supported_presentation(
    view_definition,
    presentation,
):
    view = build_view(
        _standard_view_index(view_definition),
        "composition",
        focus="bleTraceView",
        depth=5,
    )
    rendered = render_graph_data(view, focus="bleTraceView", depth=5)

    assert view["presentation"] == presentation
    assert rendered["layout"]["presentation"] == presentation
    assert "bleTraceView" not in {
        node["name"] for node in rendered["layout"]["nodes"]
    }
    assert presentation.replace("_", " ") in render_text(view).lower()
    assert "digraph" in render_dot(view)


def test_interconnection_view_uses_parts_ports_and_interface_edges():
    view = build_view(
        _standard_view_index("InterconnectionView"),
        "composition",
        focus="bleTraceView",
        depth=5,
    )
    rendered = render_graph_data(view, focus="bleTraceView", depth=5)

    nodes = {node["name"]: node for node in rendered["layout"]["nodes"]}
    assert set(nodes) == {"Alpha", "Beta"}
    assert "outlet : DataPort" in rendered["graph"]
    assert "inlet : DataPort" in rendered["graph"]
    assert "WorkA" not in rendered["graph"]
    assert "Ready" not in rendered["graph"]
    assert "DataPort" not in nodes
    assert any(
        edge["relation"] == "connect"
        and edge["source"] == "outlet"
        and edge["target"] == "inlet"
        and edge["route_cells"]
        for edge in rendered["layout"]["edges"]
    )


def test_interconnection_view_resolves_ports_through_part_usage_types():
    index = _standard_view_index("InterconnectionView")
    symbols = index.symbols()
    symbols[:] = [
        symbol
        for symbol in symbols
        if symbol["name"] not in {"outlet", "inlet"}
    ]
    alpha = next(symbol for symbol in symbols if symbol["name"] == "Alpha")
    beta = next(symbol for symbol in symbols if symbol["name"] == "Beta")
    alpha["attributes"]["partType"] = "Generic::rfSensor"
    beta["attributes"]["partType"] = "Generic::rfProcessor"
    symbols.extend(
        [
            {
                "name": "rfSensor",
                "kind": "part_usage",
                "file": "/workspace/model.sysml",
                "range": {"line": 12, "col": 0, "end_col": 8},
                "container": "Generic",
                "ancestors": ["System", "Generic"],
                "attributes": {"partType": "Generic::Sensor"},
            },
            {
                "name": "rfProcessor",
                "kind": "part_usage",
                "file": "/workspace/model.sysml",
                "range": {"line": 13, "col": 0, "end_col": 11},
                "container": "Generic",
                "ancestors": ["System", "Generic"],
                "attributes": {"partType": "Generic::DataProcessingNode"},
            },
            {
                "name": "Sensor",
                "kind": "part_def",
                "file": "/workspace/model.sysml",
                "range": {"line": 14, "col": 0, "end_col": 6},
                "container": "Generic",
                "ancestors": ["System", "Generic"],
                "attributes": {},
            },
            {
                "name": "DataProcessingNode",
                "kind": "part_def",
                "file": "/workspace/model.sysml",
                "range": {"line": 15, "col": 0, "end_col": 18},
                "container": "Generic",
                "ancestors": ["System", "Generic"],
                "attributes": {},
            },
            {
                "name": "rawOutput",
                "kind": "port_usage",
                "file": "/workspace/model.sysml",
                "range": {"line": 16, "col": 0, "end_col": 9},
                "container": "Sensor",
                "ancestors": ["System", "Generic", "Sensor"],
                "attributes": {"portType": "RawSensorDataPort"},
            },
            {
                "name": "rawInput",
                "kind": "port_usage",
                "file": "/workspace/model.sysml",
                "range": {"line": 17, "col": 0, "end_col": 8},
                "container": "DataProcessingNode",
                "ancestors": ["System", "Generic", "DataProcessingNode"],
                "attributes": {"portType": "RawSensorDataPort"},
            },
        ]
    )
    index.source_texts["/workspace/model.sysml"] = (
        index.source_texts["/workspace/model.sysml"].replace(
            "Alpha.outlet to Beta.inlet",
            "Alpha.rawOutput to Beta.rawInput",
        )
    )

    view = build_view(index, "composition", focus="bleTraceView", depth=5)
    rendered = render_graph_data(view, focus="bleTraceView", depth=5)

    nodes = {node["name"]: node for node in rendered["layout"]["nodes"]}
    assert set(nodes) == {"Alpha", "Beta"}
    assert "rawOutput : RawSensorDataPort" in rendered["graph"]
    assert "rawInput : RawSensorDataPort" in rendered["graph"]
    connection = next(
        edge
        for edge in rendered["layout"]["edges"]
        if edge["relation"] == "connect"
    )
    assert connection["source"] == "rawOutput"
    assert connection["target"] == "rawInput"
    assert connection["route_cells"]


def test_interconnection_view_omits_features_without_a_part_owner():
    symbols = [
        {
            "name": "SourcePart",
            "kind": "part_usage",
            "file": "/workspace/model.sysml",
            "range": {"line": 1, "col": 0, "end_col": 10},
            "container": "System",
            "ancestors": ["System"],
            "attributes": {},
        },
        {
            "name": "TargetPart",
            "kind": "part_usage",
            "file": "/workspace/model.sysml",
            "range": {"line": 2, "col": 0, "end_col": 10},
            "container": "System",
            "ancestors": ["System"],
            "attributes": {},
        },
        {
            "name": "InterfaceDefinition",
            "kind": "interface_def",
            "file": "/workspace/model.sysml",
            "range": {"line": 3, "col": 0, "end_col": 20},
            "container": "System",
            "ancestors": ["System"],
            "attributes": {},
        },
        {
            "name": "EndPort",
            "kind": "port_usage",
            "file": "/workspace/model.sysml",
            "range": {"line": 4, "col": 0, "end_col": 7},
            "container": "InterfaceDefinition",
            "ancestors": ["System", "InterfaceDefinition"],
            "attributes": {"portType": "DataPort"},
        },
        {
            "name": "Payload",
            "kind": "item_usage",
            "file": "/workspace/model.sysml",
            "range": {"line": 5, "col": 0, "end_col": 7},
            "container": "EndPort",
            "ancestors": ["System", "InterfaceDefinition", "EndPort"],
            "attributes": {"itemType": "Data"},
        },
    ]
    rendered = render_graph_data(
        {
            "type": "composition",
            "presentation": "interconnection",
            "nodes": symbols,
            "edges": [
                {
                    "source": "SourcePart",
                    "target": "TargetPart",
                    "relation": "connect",
                    "label": "dataLink",
                }
            ],
        }
    )

    assert {
        node["name"] for node in rendered["layout"]["nodes"]
    } == {"SourcePart", "TargetPart"}
    assert "EndPort" not in rendered["graph"]
    assert "Payload" not in rendered["graph"]
    assert any(
        edge["relation"] == "connect"
        for edge in rendered["layout"]["edges"]
    )


def test_custom_view_definition_inherits_standard_presentation():
    view = build_view(
        _standard_view_index("CustomInterconnectionView", specialized=True),
        "composition",
        focus="bleTraceView",
        depth=5,
    )

    assert view["presentation"] == "interconnection"


def test_custom_view_definition_resolves_projected_supertype_attribute():
    index = _standard_view_index("CustomInterconnectionView", specialized=True)
    custom_definition = next(
        symbol
        for symbol in index.symbols()
        if symbol["name"] == "CustomInterconnectionView"
    )
    custom_definition["attributes"]["partType"] = (
        "StandardViewDefinitions::InterconnectionView"
    )
    custom_definition["attributes"].pop("specializes", None)
    index.references_by_name.clear()

    view = build_view(index, "composition", focus="bleTraceView", depth=5)

    assert view["presentation"] == "interconnection"


def test_qualified_custom_view_type_disambiguates_same_named_definitions():
    index = _standard_view_index("DomainB::CustomView")
    view_symbol = next(
        symbol for symbol in index.symbols() if symbol["name"] == "bleTraceView"
    )
    view_symbol["attributes"]["partType"] = "DomainB::CustomView"
    index.symbols().extend(
        [
            {
                "name": "CustomView",
                "kind": "view_def",
                "file": "/workspace/model.sysml",
                "range": {"line": 12, "col": 0, "end_col": 10},
                "container": "DomainA",
                "ancestors": ["DomainA"],
                "attributes": {
                    "specializes": "StandardViewDefinitions::SequenceView"
                },
            },
            {
                "name": "CustomView",
                "kind": "view_def",
                "file": "/workspace/model.sysml",
                "range": {"line": 13, "col": 0, "end_col": 10},
                "container": "DomainB",
                "ancestors": ["DomainB"],
                "attributes": {
                    "specializes": (
                        "StandardViewDefinitions::InterconnectionView"
                    )
                },
            },
        ]
    )

    view = build_view(index, "composition", focus="bleTraceView", depth=5)

    assert view["presentation"] == "interconnection"


def test_ambiguous_unqualified_custom_view_type_keeps_generic_presentation():
    index = _standard_view_index("CustomView")
    view_symbol = next(
        symbol for symbol in index.symbols() if symbol["name"] == "bleTraceView"
    )
    view_symbol["attributes"]["partType"] = "CustomView"
    index.symbols().extend(
        [
            {
                "name": "CustomView",
                "kind": "view_def",
                "file": "/workspace/model.sysml",
                "range": {"line": 12, "col": 0, "end_col": 10},
                "container": "DomainA",
                "ancestors": ["DomainA"],
                "attributes": {
                    "specializes": "StandardViewDefinitions::SequenceView"
                },
            },
            {
                "name": "CustomView",
                "kind": "view_def",
                "file": "/workspace/model.sysml",
                "range": {"line": 13, "col": 0, "end_col": 10},
                "container": "DomainB",
                "ancestors": ["DomainB"],
                "attributes": {
                    "specializes": (
                        "StandardViewDefinitions::InterconnectionView"
                    )
                },
            },
        ]
    )

    view = build_view(index, "composition", focus="bleTraceView", depth=5)

    assert "presentation" not in view


def test_view_filters_include_filters_from_specialized_definitions():
    index = _standard_view_index("CustomView")
    view_symbol = next(
        symbol for symbol in index.symbols() if symbol["name"] == "bleTraceView"
    )
    view_symbol["attributes"]["partType"] = "CustomView"
    custom_definition = {
        "name": "CustomView",
        "kind": "view_def",
        "file": "/workspace/model.sysml",
        "range": {"line": 12, "col": 0, "end_col": 10},
        "container": "System",
        "ancestors": ["System"],
        "attributes": {
            "specializes": "BaseView",
            "viewFilters": "@SysML::ItemUsage",
        },
    }
    base_definition = {
        "name": "BaseView",
        "kind": "view_def",
        "file": "/workspace/model.sysml",
        "range": {"line": 13, "col": 0, "end_col": 8},
        "container": "System",
        "ancestors": ["System"],
        "attributes": {
            "viewFilters": "@SysML::PartUsage,@SysML::PortUsage"
        },
    }
    symbols = index.symbols() + [custom_definition, base_definition]

    filter_kinds = render_module._view_filter_kinds(
        symbols,
        [view_symbol],
    )

    assert filter_kinds == {"item_usage", "part_usage", "port_usage"}


def test_view_presentation_resolves_from_projected_typing_relationship():
    index = _standard_view_index("SequenceView")
    view_symbol = next(
        symbol for symbol in index.symbols() if symbol["name"] == "bleTraceView"
    )
    view_symbol["attributes"].pop("partType")
    reference = Reference(
        name="SysML::SequenceView",
        file="/workspace/model.sysml",
        range=Range(1, 0, 5),
        relation="typed_by",
        source="bleTraceView",
    )
    index.references_by_name[reference.name] = [reference]

    view = build_view(index, "composition", focus="bleTraceView", depth=5)

    assert view["presentation"] == "sequence"


def test_standard_view_with_unresolved_exposures_reports_an_empty_view():
    index = _standard_view_index("BrowserView")
    view_symbol = next(
        symbol for symbol in index.symbols() if symbol["name"] == "bleTraceView"
    )
    view_symbol["attributes"].pop("exposeTargets")

    view = build_view(index, "composition", focus="bleTraceView", depth=5)
    rendered = render_graph_data(view, focus="bleTraceView", depth=5)

    assert view["nodes"] == []
    assert "no resolvable model elements" in rendered["graph"]


def test_action_flow_view_promotes_actions_and_renders_flow_edges():
    index = _standard_view_index("ActionFlowView")
    reference = Reference(
        name="WorkB",
        file="/workspace/model.sysml",
        range=Range(13, 0, 5),
        relation="succession",
        source="WorkA",
    )
    index.references_by_name[reference.name] = [reference]
    view = build_view(index, "composition", focus="bleTraceView", depth=5)
    rendered = render_graph_data(view, focus="bleTraceView", depth=5)

    node_names = {node["name"] for node in rendered["layout"]["nodes"]}
    assert {"Alpha", "Beta", "WorkA", "WorkB"} <= node_names
    assert "outlet" not in node_names
    assert any(edge["relation"] == "succession" for edge in rendered["layout"]["edges"])


def test_state_transition_view_renders_transition_relationships():
    index = _standard_view_index("StateTransitionView")
    reference = Reference(
        name="Done",
        file="/workspace/model.sysml",
        range=Range(14, 0, 4),
        relation="transition",
        source="Ready",
    )
    index.references_by_name[reference.name] = [reference]
    view = build_view(index, "composition", focus="bleTraceView", depth=5)
    rendered = render_graph_data(view, focus="bleTraceView", depth=5)

    assert {node["name"] for node in rendered["layout"]["nodes"]} == {
        "Ready",
        "Done",
    }
    assert "WorkA" not in rendered["graph"]
    assert any(edge["relation"] == "transition" for edge in rendered["layout"]["edges"])


def test_state_transition_view_routes_self_transitions_outside_the_state_box():
    index = _standard_view_index("StateTransitionView")
    reference = Reference(
        name="Ready",
        file="/workspace/model.sysml",
        range=Range(14, 0, 5),
        relation="transition",
        source="Ready",
    )
    index.references_by_name[reference.name] = [reference]
    view = build_view(index, "composition", focus="bleTraceView", depth=5)
    rendered = render_graph_data(view, focus="bleTraceView", depth=5)

    node = next(node for node in rendered["layout"]["nodes"] if node["name"] == "Ready")
    edge = next(edge for edge in rendered["layout"]["edges"] if edge["relation"] == "transition")
    assert edge["route_cells"]
    assert all(
        not (node["top"] <= line <= node["bottom"] and node["left"] <= column <= node["right"])
        for line, column in edge["route_cells"]
    )


def test_sequence_view_renders_lifelines_occurrences_and_messages():
    index = _standard_view_index("SequenceView")
    reference = Reference(
        name="WorkB",
        file="/workspace/model.sysml",
        range=Range(15, 0, 5),
        relation="message",
        source="WorkA",
    )
    index.references_by_name[reference.name] = [reference]
    view = build_view(index, "composition", focus="bleTraceView", depth=5)
    rendered = render_graph_data(view, focus="bleTraceView", depth=5)

    assert "Alpha" in rendered["graph"]
    assert "Beta" in rendered["graph"]
    assert "WorkA" in rendered["graph"]
    assert "WorkB" in rendered["graph"]
    assert any(edge["relation"] == "message" for edge in rendered["layout"]["edges"])


def test_sequence_hierarchy_fallback_retains_sequence_layout_metadata():
    rendered = render_graph_data(
        {
            "type": "composition",
            "title": "SequenceView [bleTraceView]",
            "presentation": "sequence",
            "nodes": [
                {
                    "name": "NestedAction",
                    "kind": "action_usage",
                    "file": "/workspace/model.sysml",
                    "range": {"line": 3, "col": 0, "end_col": 12},
                    "container": "UnexposedPart",
                    "ancestors": ["UnexposedPart"],
                    "attributes": {},
                }
            ],
            "edges": [],
        }
    )

    assert rendered["layout"]["presentation"] == "sequence"
    assert "no exposed lifeline features" in rendered["graph"]
    assert "NestedAction" in rendered["graph"]


def test_geometry_view_uses_projected_numeric_positions_without_inference():
    index = _standard_view_index("GeometryView")
    symbols = index.symbols()
    symbols[1]["attributes"]["position"] = {"x": 2, "y": 3, "z": 4}
    symbols[2]["attributes"]["position"] = {"x": 8, "y": 9, "z": 1}
    view = build_view(index, "composition", focus="bleTraceView", depth=5)
    rendered = render_graph_data(view, focus="bleTraceView", depth=5)

    assert "Orthographic point projections" in rendered["graph"]
    assert "XY projection:" in rendered["graph"]
    assert "XZ projection:" in rendered["graph"]
    assert "YZ projection:" in rendered["graph"]
    assert "Alpha : (2, 3, 4)" in rendered["graph"]
    assert "Beta : (8, 9, 1)" in rendered["graph"]
    assert {
        node["name"]
        for node in rendered["layout"]["nodes"]
        if "point" in node
    } == {"Alpha", "Beta"}


def test_geometry_svg_uses_graphviz_neato_for_coordinate_placement(monkeypatch):
    index = _standard_view_index("GeometryView")
    symbols = index.symbols()
    symbols[1]["attributes"]["position"] = [2, 3]
    symbols[2]["attributes"]["position"] = [8, 9]
    view = build_view(index, "composition", focus="bleTraceView", depth=5)
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="<svg/>", stderr="")

    monkeypatch.setattr(render_module.subprocess, "run", fake_run)

    assert render_module.render_svg(view) == "<svg/>"
    assert commands[0][0] == "dot"
    assert "-Kneato" in commands[0]


def test_geometry_view_reports_missing_positions_instead_of_guessing():
    view = build_view(
        _standard_view_index("GeometryView"),
        "composition",
        focus="bleTraceView",
        depth=5,
    )
    rendered = render_graph_data(view, focus="bleTraceView", depth=5)

    assert "no numeric position attributes" in rendered["graph"].lower()
    assert "no spatial positions are inferred" in rendered["graph"].lower()


def test_grid_and_browser_views_use_distinct_structured_presentations():
    grid_view = build_view(
        _standard_view_index("GridView"),
        "composition",
        focus="bleTraceView",
        depth=5,
    )
    grid = render_graph_data(grid_view, focus="bleTraceView", depth=5)
    browser_view = build_view(
        _standard_view_index("BrowserView"),
        "composition",
        focus="bleTraceView",
        depth=5,
    )
    browser = render_graph_data(browser_view, focus="bleTraceView", depth=5)

    assert "| Element" in grid["graph"]
    assert "| Relations" in grid["graph"]
    assert "Alpha [part usage]" in browser["graph"]
    assert "outlet [port usage]" in browser["graph"]
    assert grid["layout"]["nodes"]
    assert browser["layout"]["nodes"]


@pytest.mark.parametrize(
    "view_definition",
    ["SequenceView", "GeometryView", "GridView", "BrowserView"],
)
def test_table_lifeline_spatial_and_browser_layouts_respect_width(view_definition):
    view = build_view(
        _standard_view_index(view_definition),
        "composition",
        focus="bleTraceView",
        depth=5,
    )

    rendered = render_graph_data(view, focus="bleTraceView", depth=5, max_width=52)

    assert max(_display_width(line) for line in rendered["graph"].splitlines()) <= 52
