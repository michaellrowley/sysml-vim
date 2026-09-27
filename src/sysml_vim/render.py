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
        for ref in refs:
            source = ref.source or Path(ref.file).stem
            if ref.relation and (not focus or source in focus_names or ref.name in focus_names):
                edges.append({"source": source, "target": ref.name, "relation": ref.relation})
        if view_type == "composition":
            edges = [e for e in edges if e["relation"] in {"typed_by", "type"}]
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
