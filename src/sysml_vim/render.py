from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

from .workspace import WorkspaceIndex


def build_view(index: WorkspaceIndex, view_type: str, focus: str | None = None, depth: int = 3) -> dict[str, Any]:
    symbols = index.symbols()
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
            for s in symbols
            if s.get("container")
        ]
        for ref in refs:
            source = ref.source or Path(ref.file).stem
            if ref.relation and (not focus or source in focus_names or ref.name in focus_names):
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
    lines = [f"View Graph: {view['type']}", ""]
    nodes_by_name = {node["name"]: node for node in view["nodes"]}
    adjacency: dict[str, list[tuple[str, str]]] = {}
    for edge in view["edges"]:
        source = edge["source"]
        target = edge["target"]
        if source == target:
            continue
        adjacency.setdefault(source, []).append((edge["relation"], target))

    for source in adjacency:
        adjacency[source] = sorted(adjacency[source], key=lambda it: (it[0], it[1]))

    if focus and focus in nodes_by_name:
        roots = [focus]
    else:
        targets = {target for children in adjacency.values() for _, target in children}
        roots = sorted([name for name in nodes_by_name if name not in targets]) or sorted(nodes_by_name)

    def label(name: str) -> str:
        node = nodes_by_name.get(name)
        return f"{name} [{node['kind']}]" if node else name

    def walk(name: str, prefix: str, level: int, stack: set[str]) -> None:
        if level >= depth:
            return
        children = adjacency.get(name, [])
        for i, (relation, target) in enumerate(children):
            last = i == len(children) - 1
            branch = "└─" if last else "├─"
            lines.append(f"{prefix}{branch} {relation} → {label(target)}")
            if target in stack:
                loop_prefix = "   " if last else "│  "
                lines.append(f"{prefix}{loop_prefix}↺ cycle")
                continue
            walk(target, prefix + ("   " if last else "│  "), level + 1, stack | {target})

    for idx, root in enumerate(roots):
        lines.append(label(root))
        walk(root, "", 0, {root})
        if idx != len(roots) - 1:
            lines.append("")

    if len(lines) == 2:
        lines.append("(no graph relationships)")
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
