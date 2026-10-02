from sysml_vim.diagram import _display_width, render_graph_data


def _symbol(name, kind, line, *, container=None, ancestors=(), signature=None):
    return {
        "name": name,
        "kind": kind,
        "file": "/workspace/model.sysml",
        "range": {"line": line, "col": 2, "end_col": 2 + len(name)},
        "container": container,
        "ancestors": list(ancestors),
        "signature": signature,
        "attributes": {},
    }


def _edge(source, target, relation, line):
    return {
        "source": source,
        "target": target,
        "relation": relation,
        "file": "/workspace/model.sysml",
        "range": {"line": line, "col": 8, "end_col": 8 + len(target)},
    }


def test_structural_diagram_uses_feature_compartments_and_typed_routes():
    view = {
        "type": "composition",
        "nodes": [
            _symbol("Hklqswumzd", "package", 1),
            _symbol("Ygkahzr", "part_def", 2, container="Hklqswumzd", ancestors=("Hklqswumzd",)),
            _symbol(
                "hxipof",
                "part_usage",
                3,
                container="Ygkahzr",
                ancestors=("Hklqswumzd", "Ygkahzr"),
                signature="part hxipof: Tegyxc;",
            ),
            _symbol("Tegyxc", "part_def", 5, container="Hklqswumzd", ancestors=("Hklqswumzd",)),
            _symbol(
                "vebfom",
                "port_usage",
                6,
                container="Tegyxc",
                ancestors=("Hklqswumzd", "Tegyxc"),
                signature="port vebfom: Gkgsiimz;",
            ),
            _symbol("Gkgsiimz", "port_def", 8, container="Hklqswumzd", ancestors=("Hklqswumzd",)),
        ],
        "edges": [
            {
                "source": "Hklqswumzd",
                "target": "Ygkahzr",
                "relation": "contains",
                "file": "/workspace/model.sysml",
                "range": {"line": 2},
            },
            _edge("hxipof", "Tegyxc", "typed_by", 3),
            _edge("vebfom", "Gkgsiimz", "typed_by", 6),
        ],
    }

    rendered = render_graph_data(view, focus="Ygkahzr", depth=5)
    assert "hxipof : Tegyxc" in rendered["graph"]
    assert "vebfom : Gkgsiimz" in rendered["graph"]
    assert rendered["graph"].count("hxipof : Tegyxc") == 1
    assert rendered["graph"].count("vebfom : Gkgsiimz") == 1
    assert "Ygkahzr.hxipof -[typed_by]-> Tegyxc" in rendered["graph"]
    graph_lines = rendered["graph"].splitlines()
    assert graph_lines[3].lstrip().startswith("┌")
    assert "┐" in rendered["graph"]
    assert "└" in rendered["graph"]

    nodes = {node["name"]: node for node in rendered["layout"]["nodes"]}
    assert set(nodes) == {"Ygkahzr", "Tegyxc", "Gkgsiimz"}
    assert len(nodes["Ygkahzr"]["features"]) == 1
    assert len(nodes["Tegyxc"]["features"]) == 1
    graph_lines = rendered["graph"].splitlines()
    for node in nodes.values():
        node_line = graph_lines[node["line"] - 1]
        name_offset = node_line.index(node["name"])
        assert node["col"] == len(node_line[:name_offset].encode("utf-8")) + 1

    for edge in rendered["layout"]["edges"]:
        for line, column in edge["route_cells"]:
            for node in nodes.values():
                assert not (
                    node["top"] <= line <= node["bottom"]
                    and node["left"] <= column <= node["right"]
                )

    assert render_graph_data(view, focus="Ygkahzr", depth=5) == rendered

    narrow = render_graph_data(view, focus="Ygkahzr", depth=5, max_width=56)
    assert narrow["layout"]["width"] <= 56
    assert max(map(_display_width, narrow["graph"].splitlines())) <= 56
    assert set(node["name"] for node in narrow["layout"]["nodes"]) == {
        "Ygkahzr",
        "Tegyxc",
        "Gkgsiimz",
    }


def test_graph_focus_includes_containing_element_and_outer_routes_avoid_boxes():
    view = {
        "type": "composition",
        "nodes": [
            _symbol("K", "part_def", 1),
            _symbol("Z", "part_def", 2),
        ],
        "edges": [
            _edge("K", "Z", "typed_by", 1),
            _edge("Z", "K", "dependency", 2),
        ],
    }
    result = render_graph_data(view)
    assert "▲" in result["graph"]
    nodes = {node["name"]: node for node in result["layout"]["nodes"]}
    assert set(nodes) == {"K", "Z"}
    assert any(edge["relation"] == "dependency" for edge in result["layout"]["edges"])
    for edge in result["layout"]["edges"]:
        for line, column in edge["route_cells"]:
            for node in nodes.values():
                assert not (
                    node["top"] <= line <= node["bottom"]
                    and node["left"] <= column <= node["right"]
                )


def test_layout_orders_layers_to_reduce_relationship_crossings():
    view = {
        "type": "dependencies",
        "nodes": [
            _symbol("K", "part_def", 1),
            _symbol("Z", "part_def", 2),
            _symbol("Q", "part_def", 3),
            _symbol("P", "part_def", 4),
        ],
        "edges": [
            _edge("K", "P", "specializes", 1),
            _edge("Z", "Q", "specializes", 2),
        ],
    }

    result = render_graph_data(view)
    node_positions = {
        node["name"]: node["top"]
        for node in result["layout"]["nodes"]
    }

    assert node_positions["K"] < node_positions["Z"]
    assert node_positions["P"] < node_positions["Q"]


def test_unconnected_definitions_pack_into_rows():
    view = {
        "type": "composition",
        "nodes": [
            _symbol(f"Element{index}", "part_def", index + 1)
            for index in range(8)
        ],
        "edges": [],
    }

    result = render_graph_data(view)
    nodes = result["layout"]["nodes"]

    assert len({node["top"] for node in nodes}) <= 3
    assert all(node["right"] < result["layout"]["width"] for node in nodes)
    for index, node in enumerate(nodes):
        for other in nodes[index + 1 :]:
            assert (
                node["bottom"] < other["top"]
                or other["bottom"] < node["top"]
                or node["right"] < other["left"]
                or other["right"] < node["left"]
            )


def test_interconnection_annotations_overflow_for_same_rank_edges():
    long_label = "connector_annotation_that_exceeds_the_viewport_width"
    view = {
        "type": "composition",
        "presentation": "interconnection",
        "nodes": [
            _symbol("Source", "part_usage", 1),
            _symbol("Branch", "part_usage", 2),
            _symbol("Target", "part_usage", 3),
        ],
        "edges": [
            {**_edge("Source", "Branch", "connect", 1), "label": "first"},
            {**_edge("Source", "Target", "connect", 2), "label": "second"},
            {**_edge("Branch", "Target", "connect", 3), "label": long_label},
        ],
    }

    rendered = render_graph_data(view, max_width=24)

    assert rendered["layout"]["width"] > 24
    edge = next(
        edge
        for edge in rendered["layout"]["edges"]
        if edge["source"] == "Branch" and edge["target"] == "Target"
    )
    assert edge["annotation"] == long_label
    graph_lines = rendered["graph"].splitlines()
    annotation_line_number = next(
        line_number
        for line_number, line in enumerate(graph_lines, 1)
        if long_label in line
    )
    annotation_line = graph_lines[annotation_line_number - 1]
    annotation_column = (
        _display_width(annotation_line[: annotation_line.index(long_label)]) + 1
    )
    assert all(
        [annotation_line_number, annotation_column + offset] in edge["route_cells"]
        for offset in range(_display_width(long_label))
    )
