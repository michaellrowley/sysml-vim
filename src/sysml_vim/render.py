from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import re
import subprocess
from typing import Any

from .diagram import render_graph_data
from .model import Reference
from .workspace import WorkspaceIndex

_VIEW_TYPE_ATTRIBUTES = ("partType", "portType", "itemType", "attributeType")
_CONNECT_ENDPOINTS = re.compile(
    r"([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*(?:\.[A-Za-z_]\w*)?)"
    r"\s+to\s+"
    r"([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*(?:\.[A-Za-z_]\w*)?)"
)


def _view_connection_edges(
    symbols: list[dict[str, Any]],
    source_texts: dict[str, str],
    exposed_names: set[str],
    filter_kinds: set[str] | None,
) -> tuple[list[dict[str, Any]], set[str]]:
    edges = []
    rendered_connections = set()
    if filter_kinds is not None and not _view_kind_is_allowed(
        "connection_usage",
        filter_kinds,
    ):
        return edges, rendered_connections
    for symbol in symbols:
        if symbol["name"] not in exposed_names or symbol["kind"].lower() != "interface":
            continue
        source_text = source_texts.get(symbol["file"], "")
        declaration = re.search(
            rf"\binterface\s+{re.escape(symbol['name'])}\s+connect\b",
            source_text,
        )
        if declaration is None:
            continue
        statement_end = source_text.find(";", declaration.end())
        if statement_end < 0:
            continue
        endpoints = _CONNECT_ENDPOINTS.search(
            source_text[declaration.end() : statement_end]
        )
        if endpoints is None:
            continue
        source_name, target_name = (
            endpoint.split(".", 1)[0].rsplit("::", 1)[-1]
            for endpoint in endpoints.groups()
        )
        if source_name not in exposed_names or target_name not in exposed_names:
            continue
        source_endpoint, target_endpoint = endpoints.groups()
        source_feature = (
            source_endpoint.rsplit(".", 1)[-1]
            if "." in source_endpoint
            else None
        )
        target_feature = (
            target_endpoint.rsplit(".", 1)[-1]
            if "." in target_endpoint
            else None
        )
        edges.append(
            {
                "source": source_name,
                "target": target_name,
                "relation": "connect",
                "label": symbol["name"],
                "source_feature": source_feature,
                "target_feature": target_feature,
                "file": symbol["file"],
                "range": symbol["range"],
            }
        )
        rendered_connections.add(symbol["name"])
    return edges, rendered_connections


def _view_kind_is_allowed(kind: str, filter_kinds: set[str]) -> bool:
    if kind in filter_kinds:
        return True
    return kind == "interface" and "connection_usage" in filter_kinds


def _view_filter_kinds(
    symbols: list[dict[str, Any]],
    view_symbols: list[dict[str, Any]],
) -> set[str] | None:
    filter_values = []
    for view_symbol in view_symbols:
        attributes = view_symbol.get("attributes", {})
        if not isinstance(attributes, dict):
            continue
        view_filters = attributes.get("viewFilters")
        if isinstance(view_filters, str):
            filter_values.extend(view_filters.split(","))
        elif isinstance(view_filters, (list, tuple)):
            filter_values.extend(view_filters)
        part_type = attributes.get("partType")
        if not isinstance(part_type, str):
            continue
        part_type_name = part_type.rsplit("::", 1)[-1]
        definitions = [
            symbol
            for symbol in symbols
            if symbol["name"] == part_type_name
            and symbol["kind"].lower() in {"view_def", "view_definition"}
        ]
        view_file = view_symbol["file"]
        definition = next(
            (symbol for symbol in definitions if symbol["file"] == view_file),
            definitions[0] if definitions else None,
        )
        definition_attributes = (
            definition.get("attributes", {}) if definition else {}
        )
        if isinstance(definition_attributes, dict):
            definition_filters = definition_attributes.get("viewFilters", [])
            if isinstance(definition_filters, str):
                filter_values.extend(definition_filters.split(","))
            elif isinstance(definition_filters, (list, tuple)):
                filter_values.extend(definition_filters)

    kinds = set()
    for value in filter_values:
        if not isinstance(value, str):
            continue
        name = value.strip().lstrip("@").rsplit("::", 1)[-1]
        if not name:
            continue
        snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        snake_case = snake_case.removesuffix("_definition") + (
            "_def" if snake_case.endswith("_definition") else ""
        )
        kinds.add(snake_case)
    return kinds or None


def _diagram_type(symbol: dict[str, Any]) -> str | None:
    attributes = symbol.get("attributes", {})
    if not isinstance(attributes, dict):
        return None
    for type_attribute in _VIEW_TYPE_ATTRIBUTES:
        type_name = attributes.get(type_attribute)
        if isinstance(type_name, str) and type_name.strip():
            return type_name.rsplit("::", 1)[-1]
    return None


def _qualified_symbol_path(symbol: dict[str, Any]) -> tuple[str, ...]:
    name = symbol.get("name")
    if not isinstance(name, str) or not name:
        return ()
    ancestors = symbol.get("ancestors", ())
    if not isinstance(ancestors, (list, tuple)) or any(
        not isinstance(ancestor, str) for ancestor in ancestors
    ):
        ancestors = ()
    return (*ancestors, name)


def _expose_target_names(
    target: str,
    symbols: list[dict[str, Any]],
    view_symbol: dict[str, Any],
) -> set[str]:
    parts = tuple(part.strip() for part in target.strip().split("::") if part.strip())
    if not parts or parts[-1] not in {"*", "**"}:
        return {parts[-1]} if parts else set()

    wildcard = parts[-1]
    scope_parts = parts[:-1]
    view_path = _qualified_symbol_path(view_symbol)
    owner_path = view_path[:-1]
    if not owner_path:
        container = view_symbol.get("container")
        if isinstance(container, str) and container:
            owner_path = (container,)

    if scope_parts:
        package_paths = set()
        for symbol in symbols:
            if symbol.get("kind", "").lower() not in {"package", "package_def"}:
                continue
            path = _qualified_symbol_path(symbol)
            if path[-len(scope_parts) :] == scope_parts:
                package_paths.add(path)
        if not package_paths:
            return set()

        def common_prefix_length(path: tuple[str, ...]) -> int:
            return sum(
                1
                for actual, expected in zip(path, owner_path)
                if actual == expected
            )

        best_common_prefix = max(
            common_prefix_length(path) for path in package_paths
        )
        if best_common_prefix == 0 and len(package_paths) > 1:
            return set()
        best_score = max(
            (
                common_prefix_length(path),
                -abs(len(path) - len(owner_path)),
            )
            for path in package_paths
        )
        scope_paths = {
            path
            for path in package_paths
            if (
                common_prefix_length(path),
                -abs(len(path) - len(owner_path)),
            )
            == best_score
        }
    else:
        scope_paths = {owner_path}

    exposed_names = set()
    for symbol in symbols:
        path = _qualified_symbol_path(symbol)
        for scope_path in scope_paths:
            if path[: len(scope_path)] != scope_path:
                continue
            relative_depth = len(path) - len(scope_path)
            if relative_depth > 0 and (wildcard == "**" or relative_depth == 1):
                exposed_names.add(symbol["name"])
                break
    return exposed_names


def _view_composition(
    symbols: list[dict[str, Any]],
    refs: list[Reference],
    focus: str,
    depth: int,
    source_texts: dict[str, str],
) -> dict[str, Any] | None:
    view_symbols = [
        symbol
        for symbol in symbols
        if symbol["name"] == focus
        and (
            symbol["kind"].lower() == "view"
            or symbol["kind"].lower().startswith("view_")
        )
    ]
    if not view_symbols:
        return None

    view_files = {symbol["file"] for symbol in view_symbols}
    view_scope = {focus}
    view_scope.update(
        symbol["name"]
        for symbol in symbols
        if symbol.get("container") == focus or focus in symbol.get("ancestors", ())
    )
    exposure_refs = [
        ref
        for ref in refs
        if (ref.relation or "").lower() in {"expose", "exposes"}
        and ref.source in view_scope
    ]
    exposed_names = {ref.name for ref in exposure_refs}
    for view_symbol in view_symbols:
        attributes = view_symbol.get("attributes", {})
        if not isinstance(attributes, dict):
            continue
        targets = attributes.get("exposeTargets", [])
        if isinstance(targets, str):
            targets = targets.split(",")
        if isinstance(targets, (list, tuple)):
            for target in targets:
                if isinstance(target, str) and target.strip():
                    exposed_names.update(
                        _expose_target_names(target, symbols, view_symbol)
                    )
    if not exposed_names:
        return None

    local_exposed_names = {
        symbol["name"]
        for symbol in symbols
        if symbol["name"] in exposed_names and symbol["file"] in view_files
    }
    exposed_symbols = [
        symbol
        for symbol in symbols
        if symbol["name"] in exposed_names
        and (
            symbol["file"] in view_files
            or symbol["name"] not in local_exposed_names
        )
    ]
    if not exposed_symbols:
        return None

    filter_kinds = _view_filter_kinds(symbols, view_symbols)
    selected_names = set(exposed_names)
    symbols_by_name = {symbol["name"]: symbol for symbol in symbols}
    for symbol in exposed_symbols:
        for parent_name in (*symbol.get("ancestors", ()), symbol.get("container")):
            parent_symbol = symbols_by_name.get(parent_name)
            if (
                parent_name
                and parent_symbol
                and parent_symbol["kind"].lower() not in {"package", "package_def"}
            ):
                selected_names.add(parent_name)

    edges = [
        {
            "source": ref.source,
            "target": ref.name,
            "relation": ref.relation,
            "file": ref.file,
            "range": asdict(ref.range),
        }
        for ref in refs
        if ref.relation
        and ref.source
        and ref.relation.lower() not in {"expose", "exposes", "contains"}
    ]
    connection_edges, rendered_connections = _view_connection_edges(
        symbols,
        source_texts,
        exposed_names,
        filter_kinds,
    )
    edges.extend(connection_edges)
    for symbol in symbols:
        attributes = symbol.get("attributes", {})
        if not isinstance(attributes, dict):
            continue
        for type_attribute in _VIEW_TYPE_ATTRIBUTES:
            type_name = attributes.get(type_attribute)
            if not isinstance(type_name, str) or not type_name.strip():
                continue
            edges.append(
                {
                    "source": symbol["name"],
                    "target": type_name.rsplit("::", 1)[-1],
                    "relation": "typed_by",
                    "file": symbol["file"],
                    "range": symbol["range"],
                }
            )

    for _ in range(max(0, depth)):
        previous_names = len(selected_names)
        for symbol in symbols:
            container = symbol.get("container")
            container_symbol = symbols_by_name.get(container)
            if (
                container in selected_names
                and container_symbol
                and container_symbol["kind"].lower() not in {"package", "package_def"}
                and (
                    filter_kinds is None
                    or _view_kind_is_allowed(
                        symbol["kind"].lower(),
                        filter_kinds,
                    )
                )
            ):
                selected_names.add(symbol["name"])
        if len(selected_names) == previous_names:
            break

    selected_names.difference_update(rendered_connections)
    visible_symbols = [
        symbol
        for symbol in symbols
        if symbol["name"] in selected_names
        and symbol["name"] != focus
        and (
            filter_kinds is None
            or _view_kind_is_allowed(symbol["kind"].lower(), filter_kinds)
        )
    ]
    visible_symbols_by_name = {symbol["name"]: symbol for symbol in visible_symbols}
    for symbol in exposed_symbols:
        type_name = _diagram_type(symbol)
        if type_name is None or symbol["name"] not in visible_symbols_by_name:
            continue
        display_symbol = visible_symbols_by_name[symbol["name"]]
        display_attributes = dict(display_symbol.get("attributes", {}))
        display_attributes["diagramType"] = type_name
        display_symbol["attributes"] = display_attributes

    for symbol in exposed_symbols:
        type_name = _diagram_type(symbol)
        if type_name is None:
            continue
        definition_matches = [
            candidate
            for candidate in symbols
            if candidate["name"] == type_name
            and candidate["kind"].lower().endswith(("_def", "_definition"))
        ]
        definition = next(
            (
                candidate
                for candidate in definition_matches
                if candidate["file"] == symbol["file"]
            ),
            definition_matches[0] if definition_matches else None,
        )
        if definition is None:
            continue
        for feature in symbols:
            if (
                feature.get("container") != definition["name"]
                or feature["file"] != definition["file"]
                or (
                    filter_kinds is not None
                    and not _view_kind_is_allowed(
                        feature["kind"].lower(),
                        filter_kinds,
                    )
                )
            ):
                continue
            projected_feature = dict(feature)
            projected_feature["container"] = symbol["name"]
            projected_feature["ancestors"] = [
                *symbol.get("ancestors", ()),
                symbol["name"],
            ]
            visible_symbols.append(projected_feature)

    visible_names = {symbol["name"] for symbol in visible_symbols}
    containment_edges = [
        {
            "source": symbol["container"],
            "target": symbol["name"],
            "relation": "contains",
            "file": symbol["file"],
            "range": symbol["range"],
        }
        for symbol in visible_symbols
        if symbol.get("container") in visible_names
    ]
    relationship_edges = [
        edge
        for edge in edges
        if edge["source"] in visible_names and edge["target"] in visible_names
    ]
    return {
        "type": "composition",
        "title": f"bdd [Package] {next(iter(view_symbols))['container']} [{focus}]",
        "nodes": visible_symbols,
        "edges": [*containment_edges, *relationship_edges],
    }


def build_view(index: WorkspaceIndex, view_type: str, focus: str | None = None, depth: int = 3) -> dict[str, Any]:
    all_symbols = index.symbols()
    symbols = all_symbols
    refs = [r for refs in index.references_by_name.values() for r in refs]

    if view_type == "composition" and focus:
        view_composition = _view_composition(
            all_symbols,
            refs,
            focus,
            depth,
            getattr(index, "source_texts", {}),
        )
        if view_composition is not None:
            return view_composition

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


def render_graph(
    view: dict[str, Any],
    focus: str | None = None,
    depth: int = 4,
    max_width: int | None = None,
) -> str:
    return render_graph_data(view, focus, depth, max_width)["graph"]


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
