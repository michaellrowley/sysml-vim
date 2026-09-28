from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import subprocess
from typing import Any

from .diagram import render_graph_data
from .workspace import WorkspaceIndex


def build_view(index: WorkspaceIndex, view_type: str, focus: str | None = None, depth: int = 3) -> dict[str, Any]:
    all_symbols = index.symbols()
    symbols = all_symbols
    refs = [r for refs in index.references_by_name.values() for r in refs]

    if focus:
        focused_symbols = [
            symbol
            for symbol in all_symbols
            if symbol["name"] == focus or symbol.get("container") == focus
        ]
        ancestor_names = {
            ancestor
            for symbol in focused_symbols
            for ancestor in symbol.get("ancestors", ())
        }
        symbols = [
            symbol
            for symbol in all_symbols
            if symbol["name"] == focus
            or symbol.get("container") == focus
            or symbol["name"] in ancestor_names
        ]

    if view_type in {"package", "tree"}:
        return {"type": "package", "nodes": symbols, "edges": []}

    if view_type in {"composition", "connections", "requirements", "traceability", "dependencies", "state", "behavior"}:
        edges: list[dict[str, Any]] = []
        focus_names = {s["name"] for s in symbols}
        containment_edges = [
            {
                "source": s["container"],
                "target": s["name"],
                "relation": "contains",
                "file": s["file"],
                "range": s["range"],
            }
            for s in all_symbols
            if s.get("container")
        ]
        for ref in refs:
            source = ref.source or Path(ref.file).stem
            if ref.relation:
                edges.append(
                    {
                        "source": source,
                        "target": ref.name,
                        "relation": ref.relation,
                        "file": ref.file,
                        "range": asdict(ref.range),
                    }
                )
        if view_type == "composition":
            edges = [e for e in edges if e["relation"] in {"typed_by", "type"}] + containment_edges
        elif view_type == "connections":
            edges = [e for e in edges if e["relation"] in {"type", "transition"}]
        elif view_type in {"requirements", "traceability"}:
            edges = [e for e in edges if e["relation"] in {"satisfy", "verify", "trace", "refine"}]
        elif view_type in {"behavior", "state"}:
            edges = [e for e in edges if e["relation"] in {"transition", "specializes"}]
        elif view_type == "dependencies":
            edges = [
                edge
                for edge in edges
                if edge["relation"]
                in {"import", "type", "typed_by", "allocate", "dependency"}
            ]
        if focus:
            visible_names = set(focus_names)
            selected_edges: list[dict[str, Any]] = []
            selected_edge_keys: set[tuple[str, str, str, str]] = set()

            def include_edge(edge: dict[str, Any]) -> None:
                edge_key = (
                    edge["source"],
                    edge["target"],
                    edge["relation"],
                    edge.get("file", ""),
                )
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
    return render_graph_data(view, focus, depth)["graph"]


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
