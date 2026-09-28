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
            _symbol("VehiclePkg", "package", 1),
            _symbol("Vehicle", "part_def", 2, container="VehiclePkg", ancestors=("VehiclePkg",)),
            _symbol(
                "engine",
                "part_usage",
                3,
                container="Vehicle",
                ancestors=("VehiclePkg", "Vehicle"),
                signature="part engine: Engine;",
            ),
            _symbol("Engine", "part_def", 5, container="VehiclePkg", ancestors=("VehiclePkg",)),
            _symbol(
                "fuelIn",
                "port_usage",
                6,
                container="Engine",
                ancestors=("VehiclePkg", "Engine"),
                signature="port fuelIn: FuelPort;",
            ),
            _symbol("FuelPort", "port_def", 8, container="VehiclePkg", ancestors=("VehiclePkg",)),
        ],
        "edges": [
            {
                "source": "VehiclePkg",
                "target": "Vehicle",
                "relation": "contains",
                "file": "/workspace/model.sysml",
                "range": {"line": 2},
            },
            _edge("engine", "Engine", "typed_by", 3),
            _edge("fuelIn", "FuelPort", "typed_by", 6),
        ],
    }

    rendered = render_graph_data(view, focus="Vehicle", depth=5)
    assert "engine : Engine" in rendered["graph"]
    assert "fuelIn : FuelPort" in rendered["graph"]
    assert rendered["graph"].count("engine : Engine") == 1
    assert rendered["graph"].count("fuelIn : FuelPort") == 1
    assert "Vehicle.engine -[typed_by]-> Engine" in rendered["graph"]
    graph_lines = rendered["graph"].splitlines()
    assert graph_lines[3].lstrip().startswith("┌")
    assert "┐" in rendered["graph"]
    assert "└" in rendered["graph"]

    nodes = {node["name"]: node for node in rendered["layout"]["nodes"]}
    assert set(nodes) == {"Vehicle", "Engine", "FuelPort"}
    assert len(nodes["Vehicle"]["features"]) == 1
    assert len(nodes["Engine"]["features"]) == 1
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

    assert render_graph_data(view, focus="Vehicle", depth=5) == rendered

    narrow = render_graph_data(view, focus="Vehicle", depth=5, max_width=56)
    assert narrow["layout"]["width"] <= 56
    assert max(map(_display_width, narrow["graph"].splitlines())) <= 56
    assert set(node["name"] for node in narrow["layout"]["nodes"]) == {
        "Vehicle",
        "Engine",
        "FuelPort",
    }


def test_graph_focus_includes_containing_element_and_outer_routes_avoid_boxes():
    view = {
        "type": "composition",
        "nodes": [
            _symbol("A", "part_def", 1),
            _symbol("B", "part_def", 2),
        ],
        "edges": [
            _edge("A", "B", "typed_by", 1),
            _edge("B", "A", "dependency", 2),
        ],
    }
    result = render_graph_data(view)
    assert "▲" in result["graph"]
    nodes = {node["name"]: node for node in result["layout"]["nodes"]}
    assert set(nodes) == {"A", "B"}
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
            _symbol("A", "part_def", 1),
            _symbol("B", "part_def", 2),
            _symbol("X", "part_def", 3),
            _symbol("Y", "part_def", 4),
        ],
        "edges": [
            _edge("A", "Y", "specializes", 1),
            _edge("B", "X", "specializes", 2),
        ],
    }

    result = render_graph_data(view)
    node_positions = {
        node["name"]: node["top"]
        for node in result["layout"]["nodes"]
    }

    assert node_positions["A"] < node_positions["B"]
    assert node_positions["Y"] < node_positions["X"]


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
