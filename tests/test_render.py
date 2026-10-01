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
