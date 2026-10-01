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
_VIEW_DEFINITION_ATTRIBUTES = (
    "partType",
    "viewType",
    "viewDefinition",
    "view_definition",
)
_STANDARD_VIEW_PRESENTATIONS = {
    "generalview": "general",
    "interconnectionview": "interconnection",
    "actionflowview": "action_flow",
    "statetransitionview": "state_transition",
    "sequenceview": "sequence",
    "geometryview": "geometry",
    "gridview": "grid",
    "browserview": "browser",
}
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
        symbol_range = symbol.get("range", {})
        start_offset = 0
        declaration_line = None
        if isinstance(symbol_range, dict) and isinstance(
            symbol_range.get("line"), int
        ):
            declaration_line = symbol_range["line"] - 1
            source_lines = source_text.splitlines(keepends=True)
            start_offset = sum(
                len(line) for line in source_lines[: max(0, declaration_line)]
            )
        declaration = re.search(
            rf"\binterface\s+{re.escape(symbol['name'])}\b"
            r"(?:\s*:\s*[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)?\s+connect\b",
            source_text[start_offset:],
        )
        if declaration is None:
            continue
        declaration_start = start_offset + declaration.start()
        if (
            declaration_line is not None
            and source_text.count("\n", 0, declaration_start) != declaration_line
        ):
            continue
        declaration_end = start_offset + declaration.end()
        statement_end = source_text.find(";", declaration_end)
        if statement_end < 0:
            continue
        endpoints = _CONNECT_ENDPOINTS.search(
            source_text[declaration_end:statement_end]
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


def _symbol_qualified_path(symbol: dict[str, Any]) -> tuple[str, ...]:
    ancestors = symbol.get("ancestors", ())
    if not isinstance(ancestors, (list, tuple)):
        ancestors = ()
    return (
        tuple(name for name in ancestors if isinstance(name, str) and name)
        + (symbol["name"],)
    )


def _symbol_identity(symbol: dict[str, Any]) -> tuple[str, str, Any, Any]:
    source_range = symbol.get("range", {})
    if not isinstance(source_range, dict):
        source_range = {}
    return (
        symbol["file"],
        symbol["name"],
        source_range.get("line", 0),
        source_range.get("col", 0),
    )


def _wildcard_exposed_symbols(
    symbols: list[dict[str, Any]],
    view_symbol: dict[str, Any],
    target: str,
    filter_kinds: set[str] | None,
) -> list[dict[str, Any]]:
    target_path = tuple(
        component
        for component in target.removesuffix("::**").split("::")
        if component
    )
    if not target_path:
        return []

    view_path = _symbol_qualified_path(view_symbol)[:-1]
    if (
        view_symbol.get("container")
        and (not view_path or view_path[-1] != view_symbol["container"])
    ):
        view_path = (*view_path, view_symbol["container"])

    package_symbols = [
        symbol
        for symbol in symbols
        if symbol["kind"].lower() in {"package", "package_def"}
    ]

    def package_rank(
        package: dict[str, Any],
    ) -> tuple[int, int, int]:
        package_path = _symbol_qualified_path(package)
        if (
            len(target_path) <= len(view_path)
            and view_path[-len(target_path) :] == target_path
            and package_path == view_path
        ):
            match_rank = 4
        elif package_path == (*view_path, *target_path):
            match_rank = 3
        elif (
            len(target_path) <= len(package_path)
            and package_path[-len(target_path) :] == target_path
        ):
            match_rank = 2
        else:
            match_rank = 0
        common_prefix = 0
        for package_part, view_part in zip(package_path, view_path):
            if package_part != view_part:
                break
            common_prefix += 1
        same_file = int(package["file"] == view_symbol["file"])
        return match_rank, common_prefix, same_file

    matching_packages = [
        package for package in package_symbols if package_rank(package)[0] > 0
    ]
    if not matching_packages:
        return []
    package = max(matching_packages, key=package_rank)
    package_path = _symbol_qualified_path(package)

    return [
        symbol
        for symbol in symbols
        if len(_symbol_qualified_path(symbol)) > len(package_path)
        and _symbol_qualified_path(symbol)[: len(package_path)] == package_path
        and (
            filter_kinds is None
            or _view_kind_is_allowed(symbol["kind"].lower(), filter_kinds)
        )
    ]


def _view_kind_is_allowed(kind: str, filter_kinds: set[str]) -> bool:
    if kind in filter_kinds:
        return True
    return kind == "interface" and "connection_usage" in filter_kinds


def _qualified_name_parts(name: str) -> tuple[str, ...]:
    return tuple(
        part.strip()
        for part in name.strip().lstrip("@").split("::")
        if part.strip()
    )


def _view_definition_candidates(
    symbols: list[dict[str, Any]],
    name: str,
    view_symbols: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    definitions = [
        symbol
        for symbol in symbols
        if symbol["kind"].lower() in {"view_def", "view_definition"}
    ]
    name_parts = _qualified_name_parts(name)
    if not name_parts:
        return []
    if len(name_parts) > 1:
        candidates = [
            symbol
            for symbol in definitions
            if _symbol_qualified_path(symbol)[-len(name_parts) :] == name_parts
        ]
        if not candidates:
            candidates = [
                symbol
                for symbol in definitions
                if symbol["name"] == name_parts[-1]
            ]
    else:
        candidates = [
            symbol for symbol in definitions if symbol["name"] == name_parts[-1]
        ]
    if len(candidates) <= 1:
        return candidates

    same_file = {
        symbol["file"]
        for symbol in view_symbols
        if isinstance(symbol.get("file"), str)
    }
    local_candidates = [
        candidate for candidate in candidates if candidate["file"] in same_file
    ]
    if len(local_candidates) == 1:
        return local_candidates
    if local_candidates:
        candidates = local_candidates

    view_paths = [_symbol_qualified_path(symbol)[:-1] for symbol in view_symbols]

    def context_score(candidate: dict[str, Any]) -> int:
        candidate_path = _symbol_qualified_path(candidate)[:-1]
        scores = []
        for view_path in view_paths:
            score = 0
            for left, right in zip(candidate_path, view_path):
                if left != right:
                    break
                score += 1
            scores.append(score)
        return max(scores, default=0)

    scores = [context_score(candidate) for candidate in candidates]
    best_score = max(scores)
    best_candidates = [
        candidate
        for candidate, score in zip(candidates, scores)
        if score == best_score
    ]
    return best_candidates if len(best_candidates) == 1 else []


def _reference_targets_definition(
    reference: Reference,
    definition: dict[str, Any],
) -> bool:
    if not isinstance(reference.source, str):
        return False
    source_parts = _qualified_name_parts(reference.source)
    if not source_parts:
        return False
    if len(source_parts) > 1:
        return (
            _symbol_qualified_path(definition)[-len(source_parts) :]
            == source_parts
        )
    return (
        source_parts[-1] == definition["name"]
        and reference.file == definition["file"]
    )


def _definition_specializations(
    definition: dict[str, Any],
    refs: list[Reference],
) -> list[str]:
    names = []
    attributes = definition.get("attributes", {})
    if isinstance(attributes, dict):
        for attribute_name in (
            "specializes",
            "specialization",
            "superTypes",
            *_VIEW_DEFINITION_ATTRIBUTES,
        ):
            value = attributes.get(attribute_name)
            values = value if isinstance(value, (list, tuple)) else [value]
            names.extend(
                item.strip().lstrip("@")
                for item in values
                if isinstance(item, str) and item.strip()
            )
    names.extend(
        reference.name.strip().lstrip("@")
        for reference in refs
        if _reference_targets_definition(reference, definition)
        and (reference.relation or "").lower()
        in {"specializes", "specialization", "type", "typed_by", "typing"}
    )
    return names


def _view_filter_kinds(
    symbols: list[dict[str, Any]],
    view_symbols: list[dict[str, Any]],
    refs: list[Reference] = (),
) -> set[str] | None:
    filter_values = []
    pending = _view_definition_names(view_symbols, refs)
    for view_symbol in view_symbols:
        attributes = view_symbol.get("attributes", {})
        if not isinstance(attributes, dict):
            continue
        view_filters = attributes.get("viewFilters")
        if isinstance(view_filters, str):
            filter_values.extend(view_filters.split(","))
        elif isinstance(view_filters, (list, tuple)):
            filter_values.extend(view_filters)

    visited: set[tuple[str, str, Any, Any]] = set()
    while pending:
        definition_name = pending.pop(0)
        candidates = _view_definition_candidates(
            symbols,
            definition_name,
            view_symbols,
        )
        for definition in candidates:
            identity = _symbol_identity(definition)
            if identity in visited:
                continue
            visited.add(identity)
            attributes = definition.get("attributes", {})
            if isinstance(attributes, dict):
                definition_filters = attributes.get("viewFilters", [])
                if isinstance(definition_filters, str):
                    filter_values.extend(definition_filters.split(","))
                elif isinstance(definition_filters, (list, tuple)):
                    filter_values.extend(definition_filters)
            pending.extend(_definition_specializations(definition, refs))

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


def _view_definition_names(
    view_symbols: list[dict[str, Any]],
    refs: list[Reference],
) -> list[str]:
    names = []
    view_names = {symbol["name"] for symbol in view_symbols}
    view_files = {symbol["file"] for symbol in view_symbols}
    for view_symbol in view_symbols:
        attributes = view_symbol.get("attributes", {})
        if isinstance(attributes, dict):
            for attribute_name in _VIEW_DEFINITION_ATTRIBUTES:
                value = attributes.get(attribute_name)
                values = value if isinstance(value, (list, tuple)) else [value]
                names.extend(
                    item.strip().lstrip("@")
                    for item in values
                    if isinstance(item, str) and item.strip()
                )
    names.extend(
        ref.name.strip().lstrip("@")
        for ref in refs
        if isinstance(ref.source, str)
        and ref.source.rsplit("::", 1)[-1] in view_names
        and ref.file in view_files
        and (ref.relation or "").lower() in {"type", "typed_by", "typing"}
    )
    return list(
        dict.fromkeys(name for name in names if isinstance(name, str) and name)
    )


def _view_presentation(
    symbols: list[dict[str, Any]],
    refs: list[Reference],
    view_symbols: list[dict[str, Any]],
) -> str | None:
    pending = _view_definition_names(view_symbols, refs)
    visited: set[tuple[str, str, Any, Any]] = set()
    while pending:
        definition_name = pending.pop(0)
        definition_parts = _qualified_name_parts(definition_name)
        if not definition_parts:
            continue
        candidates = _view_definition_candidates(
            symbols,
            definition_name,
            view_symbols,
        )
        if not candidates:
            has_matching_definition = any(
                symbol["kind"].lower() in {"view_def", "view_definition"}
                and symbol["name"] == definition_parts[-1]
                for symbol in symbols
            )
            normalized_name = re.sub(r"[^a-z]", "", definition_parts[-1].lower())
            presentation = _STANDARD_VIEW_PRESENTATIONS.get(normalized_name)
            if presentation and (
                not has_matching_definition
                or "StandardViewDefinitions" in definition_parts
            ):
                return presentation
            continue

        for definition in candidates:
            identity = _symbol_identity(definition)
            if identity in visited:
                continue
            visited.add(identity)
            normalized_name = re.sub(
                r"[^a-z]", "", definition["name"].lower()
            )
            presentation = _STANDARD_VIEW_PRESENTATIONS.get(normalized_name)
            if presentation:
                return presentation
            pending.extend(_definition_specializations(definition, refs))
    return None


def _diagram_type(symbol: dict[str, Any]) -> str | None:
    attributes = symbol.get("attributes", {})
    if not isinstance(attributes, dict):
        return None
    for type_attribute in _VIEW_TYPE_ATTRIBUTES:
        type_name = attributes.get(type_attribute)
        if isinstance(type_name, str) and type_name.strip():
            return type_name.rsplit("::", 1)[-1]
    return None


def _projected_type_names(symbol: dict[str, Any]) -> list[str]:
    attributes = symbol.get("attributes", {})
    if not isinstance(attributes, dict):
        return []
    names = []
    for attribute_name in _VIEW_TYPE_ATTRIBUTES:
        value = attributes.get(attribute_name)
        values = value if isinstance(value, (list, tuple)) else [value]
        names.extend(
            item.strip().lstrip("@")
            for item in values
            if isinstance(item, str) and item.strip()
        )
    return names


def _projected_type_candidates(
    symbols: list[dict[str, Any]],
    type_name: str,
    source_file: str | None,
) -> list[dict[str, Any]]:
    name_parts = _qualified_name_parts(type_name)
    if not name_parts:
        return []
    candidates = [
        symbol
        for symbol in symbols
        if (
            _symbol_qualified_path(symbol)[-len(name_parts) :] == name_parts
            if len(name_parts) > 1
            else symbol["name"] == name_parts[-1]
        )
    ]
    if not candidates and len(name_parts) > 1:
        candidates = [
            symbol for symbol in symbols if symbol["name"] == name_parts[-1]
        ]
    if len(candidates) <= 1:
        return candidates
    same_file = [
        candidate
        for candidate in candidates
        if candidate.get("file") == source_file
    ]
    if len(same_file) == 1:
        return same_file
    return []


def _projected_part_type_features(
    part_usage: dict[str, Any],
    symbols: list[dict[str, Any]],
    refs: list[Reference],
    filter_kinds: set[str] | None,
) -> list[dict[str, Any]]:
    pending = _projected_type_names(part_usage)
    visited: set[tuple[str, str, Any, Any]] = set()
    features = []
    feature_kinds = {
        "part_usage",
        "port_usage",
        "item_usage",
        "attribute_usage",
    }
    while pending:
        type_name = pending.pop(0)
        for type_symbol in _projected_type_candidates(
            symbols,
            type_name,
            part_usage.get("file"),
        ):
            identity = _symbol_identity(type_symbol)
            if identity in visited:
                continue
            visited.add(identity)
            kind = type_symbol["kind"].lower()
            if kind == "part_usage" or kind == "part_def":
                features.extend(
                    feature
                    for feature in symbols
                    if feature.get("container") == type_symbol["name"]
                    and feature.get("file") == type_symbol.get("file")
                    and feature.get("kind", "").lower() in feature_kinds
                    and (
                        filter_kinds is None
                        or _view_kind_is_allowed(
                            feature["kind"].lower(),
                            filter_kinds,
                        )
                    )
                )
            if kind.endswith("_def") or kind.endswith("_definition"):
                pending.extend(_definition_specializations(type_symbol, refs))
            else:
                pending.extend(_projected_type_names(type_symbol))
    return features


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

    presentation = _view_presentation(symbols, refs, view_symbols)
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
    explicit_exposed_names = {ref.name for ref in exposure_refs}
    filter_kinds = _view_filter_kinds(symbols, view_symbols, refs)
    wildcard_exposed_symbols = []
    for view_symbol in view_symbols:
        attributes = view_symbol.get("attributes", {})
        if not isinstance(attributes, dict):
            continue
        targets = attributes.get("exposeTargets", [])
        if isinstance(targets, str):
            targets = targets.split(",")
        if isinstance(targets, (list, tuple)):
            for target in targets:
                if not isinstance(target, str) or not target.strip():
                    continue
                target = target.strip()
                if target.endswith("::**"):
                    wildcard_exposed_symbols.extend(
                        _wildcard_exposed_symbols(
                            symbols,
                            view_symbol,
                            target,
                            filter_kinds,
                        )
                    )
                else:
                    explicit_exposed_names.add(target.rsplit("::", 1)[-1].strip())
    wildcard_exposed_keys = {
        _symbol_identity(symbol) for symbol in wildcard_exposed_symbols
    }
    wildcard_exposed_names = {
        symbol["name"] for symbol in wildcard_exposed_symbols
    }
    exposed_names = explicit_exposed_names | wildcard_exposed_names
    if not exposed_names:
        if presentation:
            view_symbol = view_symbols[0]
            return {
                "type": "composition",
                "title": (
                    f"{presentation.replace('_', ' ').title()} "
                    f"[{focus}]"
                ),
                "presentation": presentation,
                "issues": ["the view exposes no resolvable model elements"],
                "nodes": [],
                "edges": [],
            }
        return None

    local_exposed_names = {
        symbol["name"]
        for symbol in symbols
        if symbol["name"] in explicit_exposed_names and symbol["file"] in view_files
    }
    exposed_symbols = [
        symbol
        for symbol in symbols
        if symbol["name"] in explicit_exposed_names
        and (
            symbol["file"] in view_files
            or symbol["name"] not in local_exposed_names
        )
    ]
    exposed_symbol_keys = {_symbol_identity(symbol) for symbol in exposed_symbols}
    for symbol in wildcard_exposed_symbols:
        symbol_key = _symbol_identity(symbol)
        if symbol_key not in exposed_symbol_keys:
            exposed_symbols.append(symbol)
            exposed_symbol_keys.add(symbol_key)
    if not exposed_symbols:
        if presentation:
            return {
                "type": "composition",
                "title": f"{presentation.replace('_', ' ').title()} [{focus}]",
                "presentation": presentation,
                "issues": ["the view exposes no resolvable model elements"],
                "nodes": [],
                "edges": [],
            }
        return None

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
        exposed_symbols,
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
        and (
            symbol["name"] not in wildcard_exposed_names
            or symbol["name"] in explicit_exposed_names
            or _symbol_identity(symbol) in wildcard_exposed_keys
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

    visible_feature_owners = {
        (
            visible_symbol.get("container"),
            visible_symbol.get("name"),
            visible_symbol.get("kind"),
        )
        for visible_symbol in visible_symbols
    }
    for symbol in exposed_symbols:
        if symbol.get("kind", "").lower() != "part_usage":
            continue
        for feature in _projected_part_type_features(
            symbol,
            symbols,
            refs,
            filter_kinds,
        ):
            feature_owner_key = (
                symbol["name"],
                feature["name"],
                feature["kind"],
            )
            if feature_owner_key in visible_feature_owners:
                continue
            visible_feature_owners.add(feature_owner_key)
            projected_feature = dict(feature)
            projected_feature["file"] = symbol["file"]
            projected_feature["range"] = dict(symbol["range"])
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
    title = f"bdd [Package] {next(iter(view_symbols))['container']} [{focus}]"
    if presentation:
        title = (
            f"{presentation.replace('_', ' ').title()} "
            f"[{focus}]"
        )
    return {
        "type": "composition",
        "title": title,
        **({"presentation": presentation} if presentation else {}),
        "nodes": visible_symbols,
        "edges": [*containment_edges, *relationship_edges],
    }


def build_view(index: WorkspaceIndex, view_type: str, focus: str | None = None, depth: int = 3) -> dict[str, Any]:
    all_symbols = index.symbols()
    symbols = all_symbols
    refs = [r for refs in index.references_by_name.values() for r in refs]

    if focus:
        view_composition = _view_composition(
            all_symbols,
            refs,
            focus,
            depth,
            getattr(index, "source_texts", {}),
        )
        if view_composition is not None and (
            view_type == "composition" or view_composition.get("presentation")
        ):
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
    if view.get("presentation"):
        return render_graph_data(view)["graph"]
    lines = [f"View: {view['type']}", ""]
    issues = view.get("issues", [])
    for issue in issues:
        lines.append(f"Note: {issue}")
    if issues:
        lines.append("")
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
    presentation = view.get("presentation")
    if isinstance(presentation, str):
        graph_data = render_graph_data(view)
        graph_layout = graph_data["layout"]
        graph_name = f"{presentation}_{view.get('type', 'view')}"
        lines = [f"digraph {_dot_quote(graph_name)} {{"]
        if presentation == "sequence":
            lines.append("  rankdir=LR;")
        elif presentation in {"browser", "state_transition"}:
            lines.append("  rankdir=TB;")
        elif presentation == "geometry":
            lines.append("  layout=neato;")
            lines.append("  overlap=false;")
        else:
            lines.append("  rankdir=LR;")

        node_ids = {
            node.get("id"): f"n{index}"
            for index, node in enumerate(graph_layout.get("nodes", []))
        }
        node_ids_by_name = {
            node.get("name"): node_ids.get(node.get("id"))
            for node in graph_layout.get("nodes", [])
        }
        feature_ports: dict[tuple[str, str], str] = {}
        for node in graph_layout.get("nodes", []):
            label_lines = [
                str(node.get("name", "")),
                str(node.get("kind", "element")).replace("_", " "),
            ]
            if node.get("display_type"):
                label_lines.append(f": {node['display_type']}")
            node_features = [
                feature
                for feature in node.get("features", [])
                if feature.get("label")
            ]
            if presentation == "interconnection" and node_features:
                feature_fields = []
                for feature_index, feature in enumerate(node_features):
                    port_id = f"feature{feature_index}"
                    feature_ports[(node.get("id", ""), feature.get("name", ""))] = (
                        port_id
                    )
                    feature_label = str(feature["label"])
                    if feature.get("kind", "").lower() == "port_usage":
                        feature_label = f"● {feature_label}"
                    feature_fields.append(
                        f"<{port_id}>{_dot_record_escape(feature_label)}"
                    )
                node_label = (
                    "{"
                    + _dot_record_escape("\n".join(label_lines))
                    + "|{"
                    + "|".join(feature_fields)
                    + "}}"
                )
                shape = "record"
            else:
                feature_labels = [
                    feature.get("label", "")
                    for feature in node_features
                ]
                if feature_labels:
                    label_lines.append("\\n".join(feature_labels))
                node_label = chr(10).join(label_lines)
                shape = {
                    "interconnection": "box",
                    "action_flow": (
                        "ellipse"
                        if "action" in str(node.get("kind", "")).lower()
                        else "box"
                    ),
                    "state_transition": "box",
                    "sequence": "plaintext",
                    "geometry": "ellipse",
                    "grid": "record",
                    "browser": "plaintext",
                }.get(presentation, "box")
            attributes = [
                f"label={_dot_quote(node_label)}",
                f"shape={_dot_quote(shape)}",
            ]
            if presentation == "geometry" and isinstance(
                node.get("layout_point"), list
            ):
                point = node["layout_point"]
                if len(point) >= 2:
                    attributes.append(
                        f"pos={_dot_quote(f'{point[0]},{point[1]}!')}"
                    )
            lines.append(
                f"  {node_ids[node.get('id')]} [{', '.join(attributes)}];"
            )

        rendered_edge_keys = set()
        for edge in graph_layout.get("edges", []):
            source_id = edge.get("source_node_id") or edge.get("source_id")
            target_id = edge.get("target_node_id") or edge.get("target_id")
            source = node_ids.get(source_id) or node_ids_by_name.get(edge.get("source"))
            target = node_ids.get(target_id) or node_ids_by_name.get(edge.get("target"))
            if not source or not target:
                continue
            relation = str(edge.get("label") or edge.get("relation", "related"))
            flow_item = edge.get("flow_item")
            if flow_item:
                relation = f"{relation}: {flow_item}"
            source_feature = edge.get("source_feature")
            target_feature = edge.get("target_feature")
            if source_feature or target_feature:
                relation = (
                    f"{source_feature or ''} -[{relation}]-> "
                    f"{target_feature or ''}"
                )
            key = source, target, relation
            if key in rendered_edge_keys:
                continue
            rendered_edge_keys.add(key)
            edge_style = (
                'style="dotted", arrowhead="none"'
                if edge.get("relation") == "contains"
                else ""
            )
            attributes = [f"label={_dot_quote(relation)}"]
            source_port = feature_ports.get((source_id, source_feature or ""))
            target_port = feature_ports.get((target_id, target_feature or ""))
            if source_port:
                attributes.append(f"tailport={_dot_quote(source_port)}")
            if target_port:
                attributes.append(f"headport={_dot_quote(target_port)}")
            if edge_style:
                attributes.append(edge_style)
            lines.append(
                f"  {source} -> {target} [{', '.join(attributes)}];"
            )

        if presentation == "browser":
            for node in graph_layout.get("nodes", []):
                parent = node_ids_by_name.get(node.get("container"))
                child = node_ids.get(node.get("id"))
                if parent and child and parent != child:
                    key = parent, child, "contains"
                    if key not in rendered_edge_keys:
                        rendered_edge_keys.add(key)
                        lines.append(
                            f'  {parent} -> {child} [label="contains", '
                            'style="dotted", arrowhead="none"];'
                        )
        lines.append("}")
        return "\n".join(lines)

    lines = [f'digraph "{view["type"]}" {{', "  rankdir=LR;"]
    for node in view["nodes"]:
        lines.append(f'  "{node["name"]}" [label="{node["name"]}\\n{node["kind"]}"];')
    for edge in view["edges"]:
        lines.append(f'  "{edge["source"]}" -> "{edge["target"]}" [label="{edge["relation"]}"];')
    lines.append("}")
    return "\n".join(lines)


def _dot_quote(text: str) -> str:
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "")
        .replace("\n", "\\n")
    )
    return f'"{escaped}"'


def _dot_record_escape(text: str) -> str:
    escaped = text.replace("\\", "\\\\")
    for character in ("{", "}", "<", ">", "|"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def render_svg(view: dict[str, Any]) -> str:
    dot = render_dot(view)
    engine = "neato" if view.get("presentation") == "geometry" else "dot"
    proc = subprocess.run(
        ["dot", f"-K{engine}", "-Tsvg"],
        input=dot,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "dot failed")
    return proc.stdout
