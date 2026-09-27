from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from .workspace import WorkspaceIndex


def build_view(index: WorkspaceIndex, view_type: str, focus: str | None = None, depth: int = 3) -> dict[str, Any]:
    all_symbols = index.symbols()
    symbols = all_symbols
    refs = [r for refs in index.references_by_name.values() for r in refs]

    if focus:
        symbols = [s for s in symbols if s["name"] == focus or s.get("container") == focus]

    if view_type in {"package", "tree"}:
        return {"type": "package", "nodes": symbols, "edges": []}

    if view_type in {"composition", "connections", "requirements", "traceability", "dependencies", "state", "behavior"}:
        edges: list[dict[str, Any]] = []
        focus_names = {s["name"] for s in symbols}
        containment_edges = [
            {"source": s["container"], "target": s["name"], "relation": "contains"}
            for s in all_symbols
            if s.get("container")
        ]
        for ref in refs:
            source = ref.source or Path(ref.file).stem
            if ref.relation:
                edges.append({"source": source, "target": ref.name, "relation": ref.relation})
        if view_type == "composition":
            edges = [e for e in edges if e["relation"] in {"typed_by", "type"}] + containment_edges
        elif view_type == "connections":
            edges = [e for e in edges if e["relation"] in {"type", "transition"}]
        elif view_type in {"requirements", "traceability"}:
            edges = [e for e in edges if e["relation"] in {"satisfy", "verify", "trace", "refine"}]
        elif view_type in {"behavior", "state"}:
            edges = [e for e in edges if e["relation"] in {"transition", "specializes"}]
        elif view_type == "dependencies":
            edges = [e for e in edges if e["relation"] in {"import", "type", "typed_by", "allocate"}]
        if focus:
            visible_names = set(focus_names)
            selected_edges: list[dict[str, Any]] = []
            selected_edge_keys: set[tuple[str, str, str]] = set()

            def include_edge(edge: dict[str, Any]) -> None:
                edge_key = (edge["source"], edge["target"], edge["relation"])
                if edge_key not in selected_edge_keys:
                    selected_edge_keys.add(edge_key)
                    selected_edges.append(edge)
                visible_names.update((edge["source"], edge["target"]))

            # Keep edges touching the focus, then follow outgoing links up to the requested depth.
            for edge in edges:
                if edge["source"] in focus_names or edge["target"] in focus_names:
                    include_edge(edge)

            frontier = set(focus_names)
            expanded_names: set[str] = set()
            remaining_depth = max(0, depth)
            while frontier and remaining_depth:
                next_frontier: set[str] = set()
                for edge in edges:
                    if edge["source"] in frontier:
                        include_edge(edge)
                        if edge["target"] not in expanded_names:
                            next_frontier.add(edge["target"])
                expanded_names.update(frontier)
                frontier = next_frontier
                remaining_depth -= 1

            edges = selected_edges
            symbols = [
                symbol
                for symbol in all_symbols
                if symbol["name"] in visible_names
            ]
        if depth > 0:
            edges = edges[: depth * 200]
        return {"type": view_type, "nodes": symbols, "edges": edges}

    raise ValueError(f"Unsupported view type: {view_type}")


def render_text(view: dict[str, Any]) -> str:
    lines = [f"View: {view['type']}", ""]
    names = {n["name"] for n in view["nodes"]}
    for node in sorted(view["nodes"], key=lambda n: (n["kind"], n["name"])):
        lines.append(f"- {node['name']} [{node['kind']}] ({Path(node['file']).name}:{node['range']['line']})")
    if view["edges"]:
        lines.append("")
        lines.append("Relationships:")
        for edge in view["edges"]:
            if edge["source"] in names:
                lines.append(f"  {edge['source']} -[{edge['relation']}]-> {edge['target']}")
    return "\n".join(lines)


def render_graph(view: dict[str, Any], focus: str | None = None, depth: int = 4) -> str:
    nodes_by_name = {node["name"]: node for node in view["nodes"]}
    if not nodes_by_name:
        return f"View Graph: {view['type']} (ELK-style layered blocks)\n\n(no graph relationships)"

    edges = [edge for edge in view["edges"] if edge["source"] in nodes_by_name and edge["target"] in nodes_by_name]
    if focus and focus in nodes_by_name:
        allowed = {focus}
        frontier = [focus]
        level = 0
        while frontier and level < depth:
            nxt: list[str] = []
            for src in frontier:
                for edge in edges:
                    if edge["source"] == src and edge["target"] not in allowed:
                        allowed.add(edge["target"])
                        nxt.append(edge["target"])
            frontier = nxt
            level += 1
        nodes_by_name = {name: node for name, node in nodes_by_name.items() if name in allowed}
        edges = [edge for edge in edges if edge["source"] in nodes_by_name and edge["target"] in nodes_by_name]

    incoming: dict[str, set[str]] = {name: set() for name in nodes_by_name}
    outgoing: dict[str, list[tuple[str, str]]] = {name: [] for name in nodes_by_name}
    for edge in edges:
        incoming[edge["target"]].add(edge["source"])
        outgoing[edge["source"]].append((edge["relation"], edge["target"]))

    roots = [focus] if focus and focus in nodes_by_name else sorted([n for n, srcs in incoming.items() if not srcs], key=str.lower)
    if not roots:
        roots = sorted(nodes_by_name, key=str.lower)[:1]

    levels: dict[str, int] = {}
    queue = [(root, 0) for root in roots]
    while queue:
        name, lvl = queue.pop(0)
        if lvl > depth:
            continue
        prev = levels.get(name)
        if prev is not None and prev <= lvl:
            continue
        levels[name] = lvl
        for _, target in sorted(outgoing.get(name, []), key=lambda it: (it[0], it[1].lower())):
            queue.append((target, lvl + 1))

    for name in nodes_by_name:
        levels.setdefault(name, min(depth, 1))

    layers: dict[int, list[str]] = {}
    for name, lvl in levels.items():
        layers.setdefault(lvl, []).append(name)
    for lvl in layers:
        layers[lvl] = sorted(layers[lvl], key=lambda n: (nodes_by_name[n]["kind"], n.lower()))

    box_label_max = max(len(f"{name}:{nodes_by_name[name]['kind']}") for name in nodes_by_name)
    box_width = min(34, max(16, box_label_max + 4))
    box_height = 3
    x_gap = 8
    y_gap = 2
    max_layer = max(layers) if layers else 0
    max_nodes_col = max(len(nodes) for nodes in layers.values()) if layers else 1
    width = (max_layer + 1) * (box_width + x_gap) + 2
    height = max_nodes_col * (box_height + y_gap) + 2
    canvas = [[" " for _ in range(width)] for _ in range(height)]
    pos: dict[str, tuple[int, int]] = {}

    def put(x: int, y: int, ch: str) -> None:
        if 0 <= y < height and 0 <= x < width:
            cur = canvas[y][x]
            if cur == " " or cur == ch:
                canvas[y][x] = ch
            elif cur in {"─", "│"} and ch in {"─", "│", "┼"}:
                canvas[y][x] = "┼"
            elif ch == "▶":
                canvas[y][x] = ch

    def write_text(x: int, y: int, text: str) -> None:
        for i, ch in enumerate(text):
            if 0 <= y < height and 0 <= x + i < width and canvas[y][x + i] == " ":
                canvas[y][x + i] = ch

    def draw_box(x: int, y: int, label: str) -> None:
        put(x, y, "┌")
        put(x + box_width - 1, y, "┐")
        put(x, y + box_height - 1, "└")
        put(x + box_width - 1, y + box_height - 1, "┘")
        for ix in range(x + 1, x + box_width - 1):
            put(ix, y, "─")
            put(ix, y + box_height - 1, "─")
        put(x, y + 1, "│")
        put(x + box_width - 1, y + 1, "│")
        txt = label[: box_width - 4]
        write_text(x + 2, y + 1, txt)

    for lvl in range(max_layer + 1):
        names = layers.get(lvl, [])
        for row, name in enumerate(names):
            x = lvl * (box_width + x_gap)
            y = row * (box_height + y_gap)
            label = f"{name}:{nodes_by_name[name]['kind']}"
            draw_box(x, y, label)
            pos[name] = (x, y)

    edge_lines: list[str] = []
    for edge in edges:
        src = edge["source"]
        tgt = edge["target"]
        if src not in pos or tgt not in pos:
            continue
        sx, sy = pos[src]
        tx, ty = pos[tgt]
        start_x = sx + box_width
        start_y = sy + 1
        end_x = tx - 1
        end_y = ty + 1
        mid_x = (start_x + end_x) // 2
        for x in range(start_x, max(start_x, mid_x)):
            put(x, start_y, "─")
        if start_y <= end_y:
            for y in range(start_y, end_y + 1):
                put(mid_x, y, "│")
        else:
            for y in range(end_y, start_y + 1):
                put(mid_x, y, "│")
        for x in range(mid_x, end_x):
            put(x, end_y, "─")
        put(end_x, end_y, "▶")
        edge_lines.append(f"{src} -[{edge['relation']}]-> {tgt}")

    canvas_lines = ["".join(row).rstrip() for row in canvas]
    while canvas_lines and canvas_lines[-1] == "":
        canvas_lines.pop()
    lines = [f"View Graph: {view['type']} (ELK-style layered blocks)", ""]
    lines.extend(canvas_lines or ["(no graph relationships)"])
    if edge_lines:
        lines.extend(["", "Edges:"])
        lines.extend([f"- {line}" for line in edge_lines])
    return "\n".join(lines)


def render_dot(view: dict[str, Any]) -> str:
    lines = [f'digraph "{view["type"]}" {{', "  rankdir=LR;"]
    for node in view["nodes"]:
        lines.append(f'  "{node["name"]}" [label="{node["name"]}\\n{node["kind"]}"];')
    for edge in view["edges"]:
        lines.append(f'  "{edge["source"]}" -> "{edge["target"]}" [label="{edge["relation"]}"];')
    lines.append("}")
    return "\n".join(lines)


def render_svg(view: dict[str, Any]) -> str:
    dot = render_dot(view)
    proc = subprocess.run(["dot", "-Tsvg"], input=dot, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "dot failed")
    return proc.stdout
