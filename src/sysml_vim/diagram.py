from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import math
from pathlib import Path
import unicodedata
from typing import Any


_USAGE_KINDS = {
    "action_usage",
    "attribute_usage",
    "item_usage",
    "part_usage",
    "port_usage",
    "requirement_usage",
    "state_usage",
}
_TYPE_RELATIONS = {"type", "typed_by"}
_TYPE_ATTRIBUTES = ("partType", "portType", "itemType", "attributeType")
_PRESENTATION_NODE_KINDS = {
    "interconnection": {"part_usage"},
    "action_flow": {
        "part_usage",
        "action_usage",
        "send_action_usage",
        "accept_action_usage",
        "control_node",
        "control_node_usage",
        "fork_node",
        "join_node",
        "decision_node",
        "merge_node",
    },
    "state_transition": {"state_usage"},
}
_PRESENTATION_RELATIONS = {
    "interconnection": {
        "connect",
        "connection",
        "flow",
        "flow_connection",
        "item_flow",
        "binding",
        "delegate",
        "contains",
    },
    "action_flow": {
        "succession",
        "flow",
        "flow_connection",
        "item_flow",
        "binding",
        "bind",
        "delegate",
        "transition",
        "contains",
    },
    "state_transition": {"transition", "contains"},
}
_ROUTE_GLYPHS = {
    frozenset({"E", "W"}): "─",
    frozenset({"N", "S"}): "│",
    frozenset({"E", "S"}): "┌",
    frozenset({"W", "S"}): "┐",
    frozenset({"E", "N"}): "└",
    frozenset({"W", "N"}): "┘",
    frozenset({"E", "N", "S"}): "├",
    frozenset({"W", "N", "S"}): "┤",
    frozenset({"E", "W", "S"}): "┬",
    frozenset({"E", "W", "N"}): "┴",
    frozenset({"E", "W", "N", "S"}): "┼",
}
_GLYPH_ROUTES = {glyph: directions for directions, glyph in _ROUTE_GLYPHS.items()}
_GLYPH_ROUTES.update({"┄": frozenset({"E", "W"}), "┆": frozenset({"N", "S"})})


@dataclass(slots=True)
class DiagramFeature:
    id: str
    name: str
    kind: str
    label: str
    line_index: int = 0
    port_sides: set[str] = field(default_factory=set)


@dataclass(slots=True)
class DiagramNode:
    id: str
    name: str
    kind: str
    display_type: str | None
    file: str
    source_line: int
    container: str | None
    ancestors: tuple[str, ...]
    features: list[DiagramFeature] = field(default_factory=list)
    kind_lines: list[str] = field(default_factory=list)
    name_lines: list[str] = field(default_factory=list)
    type_lines: list[str] = field(default_factory=list)
    feature_lines: list[tuple[DiagramFeature, list[str]]] = field(default_factory=list)
    width: int = 0
    height: int = 0
    rank: int = 0
    x: int = 0
    y: int = 0


@dataclass(slots=True)
class DiagramEdge:
    id: str
    source: str
    target: str
    relation: str
    source_display: str
    target_display: str
    source_feature: str | None = None
    target_feature: str | None = None
    label: str | None = None
    flow_item: str | None = None
    route_label: str | None = None
    route: list[tuple[int, int, str]] = field(default_factory=list)


@dataclass(slots=True)
class DiagramLayout:
    nodes: list[DiagramNode]
    edges: list[DiagramEdge]
    width: int
    height: int


def _display_width(text: str) -> int:
    width = 0
    for character in text:
        if unicodedata.combining(character):
            continue
        width += 2 if unicodedata.east_asian_width(character) in {"F", "W"} else 1
    return width


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    if len(words) > 1:
        result = []
        current = ""
        for word in words:
            if _display_width(word) > width:
                if current:
                    result.append(current)
                    current = ""
                chunk = ""
                chunk_width = 0
                for character in word:
                    character_width = _display_width(character)
                    if chunk and chunk_width + character_width > width:
                        result.append(chunk)
                        chunk = ""
                        chunk_width = 0
                    chunk += character
                    chunk_width += character_width
                current = chunk
                continue
            candidate = f"{current} {word}".strip()
            if current and _display_width(candidate) > width:
                result.append(current)
                current = word
            else:
                current = candidate
        if current:
            result.append(current)
        return result

    result: list[str] = []
    current = ""
    current_width = 0
    for character in text:
        character_width = _display_width(character)
        if current and current_width + character_width > width:
            result.append(current)
            current = ""
            current_width = 0
        current += character
        current_width += character_width
    if current:
        result.append(current)
    return result or [""]


def _symbol_id(symbol: dict[str, Any]) -> str:
    source_range = symbol.get("range", {})
    return (
        f"{symbol.get('file', '')}:"
        f"{source_range.get('line', 0)}:"
        f"{source_range.get('col', 0)}:"
        f"{symbol.get('name', '')}"
    )


def _is_package(symbol: dict[str, Any]) -> bool:
    return symbol.get("kind", "").lower() in {"package", "package_def"}


def _is_definition(symbol: dict[str, Any]) -> bool:
    kind = symbol.get("kind", "").lower()
    return kind.endswith("_def") or kind.endswith("_definition")


def _display_type(symbol: dict[str, Any]) -> str | None:
    attributes = symbol.get("attributes", {})
    if not isinstance(attributes, dict):
        return None
    diagram_type = attributes.get("diagramType")
    if isinstance(diagram_type, str) and diagram_type.strip():
        return diagram_type.rsplit("::", 1)[-1]
    for attribute in _TYPE_ATTRIBUTES:
        type_name = attributes.get(attribute)
        if isinstance(type_name, str) and type_name.strip():
            return type_name.rsplit("::", 1)[-1]
    return None


def _ancestors(symbol: dict[str, Any]) -> tuple[str, ...]:
    values = symbol.get("ancestors", ())
    if isinstance(values, (list, tuple)):
        return tuple(value for value in values if isinstance(value, str))
    return ()


def _is_presentation_node(symbol: dict[str, Any], presentation: str | None) -> bool:
    kind = symbol.get("kind", "").lower()
    if kind in _PRESENTATION_NODE_KINDS.get(presentation or "", set()):
        return True
    return presentation == "action_flow" and any(
        token in kind
        for token in (
            "control",
            "fork",
            "join",
            "decision",
            "merge",
            "send_action",
            "accept_action",
        )
    )


def _is_presentation_element(
    symbol: dict[str, Any],
    presentation: str,
    state_names: set[str] | None = None,
) -> bool:
    kind = symbol.get("kind", "").lower()
    if presentation == "interconnection":
        return kind in {
            "part_usage",
            "port_usage",
            "item_usage",
            "attribute_usage",
            "connection_usage",
            "interface",
        } or "flow" in kind
    if presentation == "action_flow":
        return (
            kind in {
                "part_usage",
                "action_usage",
                "attribute_usage",
                "item_usage",
                "parameter_usage",
                "event_occurrence",
                "send_action_usage",
                "accept_action_usage",
            }
            or _is_presentation_node(symbol, presentation)
        )
    if presentation == "state_transition":
        return kind == "state_usage" or (
            kind == "action_usage"
            and symbol.get("container") in (state_names or set())
        )
    return True


def _parent_id(
    symbol: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> str | None:
    container = symbol.get("container")
    if not isinstance(container, str):
        return None
    symbol_ancestors = _ancestors(symbol)
    matches = [
        candidate
        for candidate in candidates
        if candidate.get("name") == container
        and candidate.get("file") == symbol.get("file")
    ]
    exact = [
        candidate
        for candidate in matches
        if _ancestors(candidate) == symbol_ancestors[:-1]
    ]
    if exact:
        return _symbol_id(exact[0])
    if matches:
        preceding = [
            candidate
            for candidate in matches
            if candidate.get("range", {}).get("line", 0)
            <= symbol.get("range", {}).get("line", 0)
        ]
        if preceding:
            return _symbol_id(max(preceding, key=lambda item: item["range"]["line"]))
    return None


def _pick_symbol(
    candidates: list[dict[str, Any]],
    name: str,
    file: str | None,
    line: int | None,
    *,
    prefer_definition: bool = False,
) -> dict[str, Any] | None:
    matching = [symbol for symbol in candidates if symbol.get("name") == name]
    if file:
        same_file = [symbol for symbol in matching if symbol.get("file") == file]
        if same_file:
            matching = same_file
    if prefer_definition:
        definitions = [symbol for symbol in matching if _is_definition(symbol)]
        if definitions:
            matching = definitions
    if not matching:
        return None
    if line is not None:
        return min(
            matching,
            key=lambda symbol: abs(symbol.get("range", {}).get("line", 0) - line),
        )
    return min(
        matching,
        key=lambda symbol: (
            symbol.get("file", ""),
            symbol.get("range", {}).get("line", 0),
        ),
    )


def _feature_label(
    symbol: dict[str, Any],
    type_name: str | None,
) -> str:
    name = symbol.get("name", "")
    if type_name:
        return f"{name} : {type_name}"
    attributes = symbol.get("attributes", {})
    if isinstance(attributes, dict):
        for type_attribute in ("partType", "portType", "itemType", "attributeType"):
            attribute_type = attributes.get(type_attribute)
            if isinstance(attribute_type, str) and attribute_type.strip():
                return f"{name} : {attribute_type.rsplit('::', 1)[-1]}"
    direction = attributes.get("direction") if isinstance(attributes, dict) else None
    if isinstance(direction, str) and direction:
        return f"{direction} {name}"
    signature = symbol.get("signature")
    if isinstance(signature, str) and signature:
        text = signature.strip().rstrip(";")
        first, separator, remainder = text.partition(" ")
        if separator and first in {
            "action",
            "attribute",
            "item",
            "part",
            "port",
            "requirement",
            "state",
        }:
            return remainder
        return text
    return name


def _build_diagram_nodes(
    symbols: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    presentation: str | None = None,
) -> tuple[list[DiagramNode], dict[str, str]]:
    symbol_ids = {_symbol_id(symbol): symbol for symbol in symbols}
    candidates = [
        symbol
        for symbol in symbols
        if (
            presentation not in _PRESENTATION_NODE_KINDS
            and _is_definition(symbol)
            and not _is_package(symbol)
        )
        or _is_presentation_node(symbol, presentation)
    ]
    for symbol in symbols:
        if _is_package(symbol) or _symbol_id(symbol) in {
            _symbol_id(candidate) for candidate in candidates
        }:
            continue
        if _parent_id(symbol, candidates) is None and not (
            presentation == "interconnection"
            and symbol.get("kind", "").lower() != "part_usage"
        ):
            candidates.append(symbol)

    feature_owner: dict[str, str] = {}
    feature_symbols: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for symbol in symbols:
        symbol_id = _symbol_id(symbol)
        if symbol_id not in symbol_ids or any(
            _symbol_id(candidate) == symbol_id for candidate in candidates
        ):
            continue
        parent = _parent_id(symbol, candidates)
        if parent:
            feature_owner[symbol_id] = parent
            feature_symbols[parent].append(symbol)

    type_names: dict[str, str] = {}
    for edge in edges:
        if edge.get("relation") not in _TYPE_RELATIONS:
            continue
        line = edge.get("range", {}).get("line")
        source_symbol = _pick_symbol(
            symbols,
            edge.get("source", ""),
            edge.get("file"),
            line if isinstance(line, int) else None,
        )
        if source_symbol is not None:
            type_names[_symbol_id(source_symbol)] = edge.get("target", "")

    diagram_nodes = []
    for symbol in candidates:
        node_id = _symbol_id(symbol)
        features = []
        for feature_symbol in sorted(
            feature_symbols.get(node_id, []),
            key=lambda feature: (
                feature.get("range", {}).get("line", 0),
                feature.get("name", "").casefold(),
            ),
        ):
            feature_id = _symbol_id(feature_symbol)
            features.append(
                DiagramFeature(
                    id=feature_id,
                    name=feature_symbol.get("name", ""),
                    kind=feature_symbol.get("kind", ""),
                    label=_feature_label(
                        feature_symbol,
                        type_names.get(feature_id),
                    ),
                )
            )
        diagram_nodes.append(
            DiagramNode(
                id=node_id,
                name=symbol.get("name", ""),
                kind=symbol.get("kind", "element"),
                display_type=(
                    _display_type(symbol)
                ),
                file=symbol.get("file", ""),
                source_line=symbol.get("range", {}).get("line", 0),
                container=symbol.get("container"),
                ancestors=_ancestors(symbol),
                features=features,
            )
        )

    return diagram_nodes, feature_owner


def _build_diagram_edges(
    symbols: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    nodes: list[DiagramNode],
    feature_owner: dict[str, str],
    presentation: str | None = None,
) -> list[DiagramEdge]:
    node_ids = {node.id for node in nodes}
    feature_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    symbol_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for symbol in symbols:
        symbol_by_name[symbol.get("name", "")].append(symbol)
        if _symbol_id(symbol) in feature_owner:
            feature_by_name[symbol.get("name", "")].append(symbol)

    def endpoint_feature_symbol(
        name: str,
        owner: str,
        file: str | None,
        line: int | None,
    ) -> dict[str, Any] | None:
        candidates = feature_by_name.get(name, [])
        owned_candidates = [
            candidate
            for candidate in candidates
            if candidate.get("container") == owner or owner in _ancestors(candidate)
        ]
        return _pick_symbol(
            owned_candidates or candidates,
            name,
            file,
            line,
        )

    diagram_edges = []
    seen: set[tuple[str, str, str, str | None, str | None]] = set()
    for edge in edges:
        relation = edge.get("relation")
        if not isinstance(relation, str):
            continue
        if relation == "contains":
            if (
                presentation not in _PRESENTATION_NODE_KINDS
                or relation not in _PRESENTATION_RELATIONS.get(presentation, set())
            ):
                continue
            source_symbol = _pick_symbol(
                symbols,
                edge.get("source", ""),
                edge.get("file"),
                edge.get("range", {}).get("line"),
            )
            target_symbol = _pick_symbol(
                symbols,
                edge.get("target", ""),
                edge.get("file"),
                edge.get("range", {}).get("line"),
            )
            if source_symbol is None or target_symbol is None:
                continue
            source_id = _symbol_id(source_symbol)
            target_id = _symbol_id(target_symbol)
            if source_id not in node_ids or target_id not in node_ids:
                continue
            key = (source_id, target_id, relation, None, None)
            if key in seen:
                continue
            seen.add(key)
            node_by_id = {node.id: node for node in nodes}
            diagram_edges.append(
                DiagramEdge(
                    id=f"{source_id}->{target_id}:{relation}:{len(diagram_edges)}",
                    source=source_id,
                    target=target_id,
                    relation=relation,
                    source_display=node_by_id[source_id].name,
                    target_display=node_by_id[target_id].name,
                )
            )
            continue
        if (
            presentation in _PRESENTATION_RELATIONS
            and relation not in _PRESENTATION_RELATIONS[presentation]
        ):
            continue
        edge_line = edge.get("range", {}).get("line")
        edge_line = edge_line if isinstance(edge_line, int) else None
        source_feature_name = edge.get("source_feature")
        target_feature_name = edge.get("target_feature")
        source_feature_symbol = (
            endpoint_feature_symbol(
                source_feature_name,
                edge.get("source", ""),
                edge.get("file"),
                edge_line,
            )
            if isinstance(source_feature_name, str)
            else None
        )
        target_feature_symbol = (
            endpoint_feature_symbol(
                target_feature_name,
                edge.get("target", ""),
                edge.get("file"),
                edge_line,
            )
            if isinstance(target_feature_name, str)
            else None
        )
        source_symbol = _pick_symbol(
            feature_by_name.get(edge.get("source", ""), []),
            edge.get("source", ""),
            edge.get("file"),
            edge_line,
        )
        if source_feature_symbol is not None:
            source_symbol = source_feature_symbol
        if source_symbol is None:
            source_symbol = _pick_symbol(
                symbols,
                edge.get("source", ""),
                edge.get("file"),
                edge_line,
            )
        target_symbol = _pick_symbol(
            symbols,
            edge.get("target", ""),
            None,
            None,
            prefer_definition=True,
        )
        if target_feature_symbol is not None:
            target_symbol = target_feature_symbol
        if source_symbol is None or target_symbol is None:
            continue

        source_id = _symbol_id(source_symbol)
        source_feature = source_id if source_id in feature_owner else None
        source_node = feature_owner.get(source_id, source_id)
        target_id = _symbol_id(target_symbol)
        target_node = feature_owner.get(target_id, target_id)
        if (
            source_node not in node_ids
            or target_node not in node_ids
            or (
                source_node == target_node
                and presentation != "state_transition"
            )
        ):
            continue
        target_feature = target_id if target_id in feature_owner else None
        key = (source_node, target_node, relation, source_feature, target_feature)
        if key in seen:
            continue
        seen.add(key)
        flow_item = edge.get("flow_item")
        if not isinstance(flow_item, str) or not flow_item.strip():
            flow_item = None
        if presentation == "interconnection" and relation.lower() in {
            "flow",
            "flow_connection",
            "item_flow",
        }:
            if flow_item is None:
                for flow_symbol in (target_symbol, source_symbol):
                    flow_kind = flow_symbol.get("kind", "").lower()
                    if (
                        flow_kind in {"item_usage", "item_def"}
                        or "flow" in flow_kind
                    ):
                        flow_item = _feature_label(flow_symbol, None)
                        break
            if flow_item is None and isinstance(edge.get("label"), str):
                flow_item = edge["label"]
        route_label = None
        if presentation == "interconnection" and relation.lower() != "contains":
            if relation.lower() in {"flow", "flow_connection", "item_flow"}:
                flow_name = str(flow_item or edge.get("label") or relation)
                route_label = f"◆ {flow_name.split(':', 1)[0].strip()}"
            else:
                route_label = str(edge.get("label") or relation)
        node_by_id = {node.id: node for node in nodes}
        source_display = node_by_id[source_node].name
        if source_feature:
            source_display += "." + source_symbol.get("name", "")
        diagram_edges.append(
            DiagramEdge(
                id=f"{source_node}->{target_node}:{relation}:{len(diagram_edges)}",
                source=source_node,
                target=target_node,
                relation=relation,
                source_display=source_display,
                target_display=(
                    node_by_id[target_node].name
                    + ("." + target_symbol.get("name", "") if target_feature else "")
                ),
                source_feature=source_feature,
                target_feature=target_feature,
                label=edge.get("label"),
                flow_item=flow_item,
                route_label=route_label,
            )
        )
    return diagram_edges


def _mark_interconnection_ports(
    nodes: list[DiagramNode],
    edges: list[DiagramEdge],
    presentation: str | None,
) -> None:
    if presentation != "interconnection":
        return
    features_by_id = {
        feature.id: feature
        for node in nodes
        for feature in node.features
    }
    for edge in edges:
        source_feature = features_by_id.get(edge.source_feature or "")
        if source_feature and source_feature.kind.lower() == "port_usage":
            source_feature.port_sides.add("right")
        target_feature = features_by_id.get(edge.target_feature or "")
        if target_feature and target_feature.kind.lower() == "port_usage":
            target_feature.port_sides.add("left")
    for feature in features_by_id.values():
        if feature.kind.lower() == "port_usage" and not feature.port_sides:
            feature.port_sides.add("right")


def _assign_ranks(nodes: list[DiagramNode], edges: list[DiagramEdge]) -> None:
    by_id = {node.id: node for node in nodes}
    outgoing: dict[str, list[str]] = defaultdict(list)
    incoming: dict[str, int] = {node.id: 0 for node in nodes}
    for edge in edges:
        outgoing[edge.source].append(edge.target)
        incoming[edge.target] += 1

    roots = sorted(
        (node.id for node in nodes if incoming[node.id] == 0),
        key=lambda node_id: (by_id[node_id].source_line, by_id[node_id].name.casefold()),
    )
    if not roots and nodes:
        roots = [min(nodes, key=lambda node: (node.source_line, node.name.casefold())).id]
    ranks: dict[str, int] = {}
    queue = deque((node_id, 0) for node_id in roots)
    while queue:
        node_id, rank = queue.popleft()
        if node_id in ranks and ranks[node_id] <= rank:
            continue
        ranks[node_id] = rank
        for target_id in sorted(outgoing[node_id]):
            queue.append((target_id, rank + 1))
    for node in nodes:
        node.rank = ranks.get(node.id, 0)

    layers: dict[int, list[DiagramNode]] = defaultdict(list)
    for node in nodes:
        layers[node.rank].append(node)
    for _ in range(4):
        for direction in (1, -1):
            ranks_in_order = sorted(layers)
            if direction < 0:
                ranks_in_order.reverse()
            position = {
                node.id: index
                for rank in ranks_in_order
                for index, node in enumerate(layers[rank])
            }
            neighbor_map: dict[str, list[str]] = defaultdict(list)
            for edge in edges:
                if direction > 0 and by_id[edge.target].rank == by_id[edge.source].rank + 1:
                    neighbor_map[edge.target].append(edge.source)
                elif direction < 0 and by_id[edge.source].rank == by_id[edge.target].rank - 1:
                    neighbor_map[edge.source].append(edge.target)
            for rank in ranks_in_order:
                layer = layers[rank]
                stable_order = {node.id: position[node.id] for node in layer}
                layer.sort(
                    key=lambda node: (
                        sum(position[item] for item in neighbor_map[node.id])
                        / len(neighbor_map[node.id])
                        if neighbor_map[node.id]
                        else stable_order[node.id],
                        stable_order[node.id],
                    )
                )
                for index, node in enumerate(layer):
                    position[node.id] = index
    nodes[:] = [
        node
        for rank in sorted(layers)
        for node in layers[rank]
    ]


def _prepare_node_text(
    nodes: list[DiagramNode],
    max_content_width: int = 48,
) -> None:
    for node in nodes:
        feature_labels = [feature.label for feature in node.features]
        longest = max(
            [
                _display_width(node.name),
                _display_width(node.display_type or ""),
                _display_width(f"«{node.kind.replace('_', ' ')}»"),
            ]
            + [_display_width(label) for label in feature_labels],
            default=0,
        )
        content_width = min(max_content_width, max(8, longest))
        node.kind_lines = _wrap(f"«{node.kind.replace('_', ' ')}»", content_width)
        node.name_lines = _wrap(node.name, content_width)
        node.type_lines = (
            _wrap(node.display_type, content_width)
            if node.display_type
            else []
        )
        node.feature_lines = [
            (feature, _wrap(feature.label, content_width))
            for feature in node.features
        ]
        next_feature_line = (
            2
            + len(node.kind_lines)
            + len(node.name_lines)
            + len(node.type_lines)
        )
        for feature, lines in node.feature_lines:
            feature.line_index = next_feature_line
            next_feature_line += len(lines)
        node.width = content_width + 4
        node.height = (
            2
            + len(node.kind_lines)
            + len(node.name_lines)
            + len(node.type_lines)
            + (1 if node.feature_lines else 0)
            + sum(len(lines) for _, lines in node.feature_lines)
        )


def _position_nodes(
    nodes: list[DiagramNode],
    edges: list[DiagramEdge],
    max_width: int | None = None,
) -> tuple[int, int]:
    node_by_id = {node.id: node for node in nodes}
    linked_ids = {
        node_id
        for edge in edges
        for node_id in (edge.source, edge.target)
    }
    linked_nodes = [node for node in nodes if node.id in linked_ids]
    isolated_nodes = [node for node in nodes if node.id not in linked_ids]
    layers: dict[int, list[DiagramNode]] = defaultdict(list)
    for node in linked_nodes:
        layers[node.rank].append(node)

    rank_width = {
        rank: max(node.width for node in layer)
        for rank, layer in layers.items()
    }
    edge_counts: dict[tuple[int, int], int] = defaultdict(int)
    route_label_widths: dict[tuple[int, int], list[int]] = defaultdict(list)
    for edge in edges:
        source_rank = node_by_id[edge.source].rank
        target_rank = node_by_id[edge.target].rank
        if target_rank == source_rank + 1:
            edge_counts[(source_rank, target_rank)] += 1
        if edge.route_label and source_rank != target_rank:
            for rank in range(min(source_rank, target_rank), max(source_rank, target_rank)):
                route_label_widths[(rank, rank + 1)].append(
                    _display_width(edge.route_label)
                )

    x_positions: dict[int, int] = {}
    x = 2
    if layers:
        max_rank = max(layers)
        base_gaps = {}
        annotated_gaps = {}
        for rank in range(max_rank):
            count = edge_counts.get((rank, rank + 1), 0)
            base_gap = (
                max(8, count + 5)
                if max_width is None
                else count + 2
            )
            base_gaps[rank] = base_gap
            label_widths = route_label_widths.get((rank, rank + 1), [])
            annotated_gaps[rank] = max(
                base_gap,
                sum(label_widths) + count + 1 if label_widths else base_gap,
            )
        for rank in range(max_rank + 1):
            x_positions[rank] = x
            x += rank_width.get(rank, 0)
            if rank < max_rank:
                x += annotated_gaps[rank]

    for rank in sorted(layers):
        y = 0
        for node in layers[rank]:
            node.x = x_positions[rank]
            node.y = y
            y += node.height + 2

    component_bottom = max(
        (node.y + node.height for node in linked_nodes),
        default=0,
    )
    outer_edge_count = sum(
        1
        for edge in edges
        if node_by_id[edge.target].rank != node_by_id[edge.source].rank + 1
    )
    isolated_y = (
        component_bottom + outer_edge_count * 2 + 2
        if linked_nodes
        else 0
    )
    target_width = max(
        x + 2 if layers else 0,
        max_width or 70,
        max((node.width + 4 for node in isolated_nodes), default=0),
    )
    isolated_x = 2
    row_y = isolated_y
    row_height = 0
    for node in isolated_nodes:
        if isolated_x > 2 and isolated_x + node.width + 2 > target_width:
            isolated_x = 2
            row_y += row_height + 2
            row_height = 0
        node.x = isolated_x
        node.y = row_y
        isolated_x += node.width + 4
        row_height = max(row_height, node.height)

    width = max(
        x + 2 if layers else 0,
        max((node.x + node.width + 2 for node in isolated_nodes), default=0),
    )
    self_loops: dict[str, int] = defaultdict(int)
    for edge in edges:
        if edge.source == edge.target:
            self_loops[edge.source] += 1
    for node_id, loop_count in self_loops.items():
        node = node_by_id[node_id]
        width = max(width, node.x + node.width + 5 + (loop_count - 1) * 2)
    height = max(
        component_bottom + outer_edge_count * 2 + 3,
        max((node.y + node.height for node in isolated_nodes), default=0) + 2,
        1,
    )
    nodes.sort(key=lambda node: (node.y, node.x, node.name.casefold()))
    return width, height


def _add_route(
    edge: DiagramEdge,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    lane: int | None = None,
    outer_y: int | None = None,
) -> None:
    connections: dict[tuple[int, int], set[str]] = defaultdict(set)

    def horizontal(y: int, start_x: int, end_x: int) -> None:
        if start_x > end_x:
            start_x, end_x = end_x, start_x
        for x in range(start_x, end_x + 1):
            if x > start_x:
                connections[(x, y)].add("W")
            if x < end_x:
                connections[(x, y)].add("E")

    def vertical(x: int, start_y: int, end_y: int) -> None:
        if start_y > end_y:
            start_y, end_y = end_y, start_y
        for y in range(start_y, end_y + 1):
            if y > start_y:
                connections[(x, y)].add("N")
            if y < end_y:
                connections[(x, y)].add("S")

    if lane is not None:
        horizontal(start[1], start[0], lane)
        vertical(lane, start[1], end[1])
        arrow_x = end[0] - 1
        horizontal(end[1], lane, arrow_x)
        connections.pop((arrow_x, end[1]), None)
        edge.route = [
            (x, y, _ROUTE_GLYPHS.get(frozenset(directions), "─"))
            for (x, y), directions in sorted(
                connections.items(), key=lambda item: (item[0][1], item[0][0])
            )
        ]
        edge.route.append((arrow_x, end[1], "▶"))
    elif outer_y is not None:
        vertical(start[0], start[1], outer_y)
        horizontal(min(start[0], end[0]), outer_y, max(start[0], end[0]))
        vertical(end[0], end[1], outer_y)
        connections.pop(end, None)
        edge.route = [
            (x, y, _ROUTE_GLYPHS.get(frozenset(directions), "─"))
            for (x, y), directions in sorted(
                connections.items(), key=lambda item: (item[0][1], item[0][0])
            )
        ]
        edge.route.append((end[0], end[1], "▲"))


def _route_edges(
    nodes: list[DiagramNode],
    edges: list[DiagramEdge],
) -> None:
    node_by_id = {node.id: node for node in nodes}
    source_feature_by_id = {
        feature.id: (node, feature)
        for node in nodes
        for feature in node.features
    }
    forward: dict[tuple[int, int], list[DiagramEdge]] = defaultdict(list)
    other: list[DiagramEdge] = []
    self_loop_indices: dict[str, int] = defaultdict(int)
    for edge in edges:
        if edge.source == edge.target:
            node = node_by_id[edge.source]
            loop_index = self_loop_indices[edge.source]
            self_loop_indices[edge.source] += 1
            start_x = node.x + node.width
            outer_x = start_x + 3 + loop_index * 2
            start_y = node.y + 1 + len(node.kind_lines)
            end_y = max(
                start_y + 1,
                node.y + node.height - 2 - loop_index,
            )
            connections: dict[tuple[int, int], set[str]] = defaultdict(set)
            for x in range(start_x, outer_x + 1):
                if x > start_x:
                    connections[(x, start_y)].add("W")
                if x < outer_x:
                    connections[(x, start_y)].add("E")
            for y in range(start_y, end_y + 1):
                if y > start_y:
                    connections[(outer_x, y)].add("N")
                if y < end_y:
                    connections[(outer_x, y)].add("S")
            for x in range(start_x, outer_x + 1):
                if x > start_x:
                    connections[(x, end_y)].add("W")
                if x < outer_x:
                    connections[(x, end_y)].add("E")
            edge.route = [
                (x, y, _ROUTE_GLYPHS.get(frozenset(directions), "─"))
                for (x, y), directions in sorted(
                    connections.items(),
                    key=lambda item: (item[0][1], item[0][0]),
                )
            ]
            edge.route.append((start_x, end_y, "◀"))
            continue
        source = node_by_id[edge.source]
        target = node_by_id[edge.target]
        if target.rank == source.rank + 1:
            forward[(source.rank, target.rank)].append(edge)
        else:
            other.append(edge)

    for rank_pair, rank_edges in forward.items():
        source_rank, _ = rank_pair
        rank_edges.sort(
            key=lambda edge: (
                node_by_id[edge.source].y,
                node_by_id[edge.target].y,
                edge.relation,
                edge.source_display.casefold(),
            )
        )
        for lane_index, edge in enumerate(rank_edges):
            source = node_by_id[edge.source]
            target = node_by_id[edge.target]
            feature_anchor = source_feature_by_id.get(edge.source_feature or "")
            target_feature_anchor = source_feature_by_id.get(edge.target_feature or "")
            source_row = (
                source.y + feature_anchor[1].line_index
                if feature_anchor
                else source.y + 1 + len(source.kind_lines)
            )
            target_row = (
                target.y + target_feature_anchor[1].line_index
                if target_feature_anchor
                else target.y + 1 + len(target.kind_lines)
            )
            start_x = source.x + source.width
            end_x = target.x
            lane_x = min(start_x + lane_index + 1, end_x - 2)
            _add_route(edge, (start_x, source_row), (end_x, target_row), lane=lane_x)

    other.sort(
        key=lambda edge: (
            node_by_id[edge.source].source_line,
            edge.relation,
            edge.source_display.casefold(),
        )
    )
    linked_nodes = {
        node_id
        for edge in edges
        for node_id in (edge.source, edge.target)
    }
    outer_lane_y = max(
        (node_by_id[node_id].y + node_by_id[node_id].height for node_id in linked_nodes),
        default=0,
    ) + 1
    for index, edge in enumerate(other):
        source = node_by_id[edge.source]
        target = node_by_id[edge.target]
        source_x = source.x + source.width // 2
        target_x = target.x + target.width // 2
        source_feature = source_feature_by_id.get(edge.source_feature or "")
        target_feature = source_feature_by_id.get(edge.target_feature or "")
        if source_feature:
            source_x = source.x + source.width
            source_y = source.y + source_feature[1].line_index
        else:
            source_y = source.y + source.height
        if target_feature:
            target_x = target.x - 1
            target_y = target.y + target_feature[1].line_index
        else:
            target_y = target.y + target.height
        _add_route(
            edge,
            (source_x, source_y),
            (target_x, target_y),
            outer_y=outer_lane_y + index * 2,
        )


def _mark_flow_routes(edges: list[DiagramEdge]) -> None:
    flow_relations = {"flow", "flow_connection", "item_flow"}
    for edge in edges:
        if edge.relation.lower() not in flow_relations:
            continue
        horizontal_by_row: dict[int, list[int]] = defaultdict(list)
        for x, y, glyph in edge.route:
            if {"E", "W"} & _GLYPH_ROUTES.get(glyph, frozenset()):
                horizontal_by_row[y].append(x)
        if not horizontal_by_row:
            continue
        row = max(horizontal_by_row, key=lambda item: len(horizontal_by_row[item]))
        columns = sorted(horizontal_by_row[row])
        marker_column = columns[len(columns) // 2]
        edge.route = [
            (x, y, "◆" if (x, y) == (marker_column, row) else glyph)
            for x, y, glyph in edge.route
        ]


def _route_annotation_positions(
    edges: list[DiagramEdge],
) -> dict[str, tuple[int, int, str]]:
    route_cells_by_id = {
        edge.id: {(x, y) for x, y, _ in edge.route}
        for edge in edges
    }
    all_route_cells = set().union(*route_cells_by_id.values())
    occupied: dict[int, list[tuple[int, int]]] = defaultdict(list)
    annotations = {}
    for edge in edges:
        label = edge.route_label
        if not label:
            continue
        label_width = _display_width(label)
        horizontal_by_row: dict[int, list[int]] = defaultdict(list)
        for x, y, glyph in edge.route:
            if {"E", "W"} & _GLYPH_ROUTES.get(glyph, frozenset()):
                horizontal_by_row[y].append(x)

        runs = []
        for row, columns in horizontal_by_row.items():
            run_start = None
            previous_column = None
            for column in sorted(set(columns)):
                if run_start is None or column > previous_column + 1:
                    if run_start is not None:
                        runs.append((row, run_start, previous_column))
                    run_start = column
                previous_column = column
            if run_start is not None:
                runs.append((row, run_start, previous_column))
        runs.sort(key=lambda run: run[2] - run[1], reverse=True)

        other_routes = all_route_cells - route_cells_by_id[edge.id]
        for row, run_start, run_end in runs:
            if run_end - run_start + 1 < label_width:
                continue
            center_start = run_start + (run_end - run_start + 1 - label_width) // 2
            starts = range(run_start, run_end - label_width + 2)
            for start in sorted(starts, key=lambda column: abs(column - center_start)):
                end = start + label_width - 1
                if any((column, row) in other_routes for column in range(start, end + 1)):
                    continue
                if any(
                    start <= occupied_end and end >= occupied_start
                    for occupied_start, occupied_end in occupied[row]
                ):
                    continue
                annotations[edge.id] = (start, row, label)
                occupied[row].append((start, end))
                break
            if edge.id in annotations:
                break
    return annotations


def _ensure_route_annotations(
    nodes: list[DiagramNode],
    edges: list[DiagramEdge],
    width: int,
    height: int,
) -> tuple[dict[str, tuple[int, int, str]], int, int]:
    annotations = _route_annotation_positions(edges)
    missing_edges = [
        edge
        for edge in edges
        if edge.route_label and edge.id not in annotations
    ]
    if not missing_edges:
        return annotations, width, height

    node_bottom = max(
        (node.y + node.height for node in nodes),
        default=0,
    )
    node_right = max(
        (node.x + node.width for node in nodes),
        default=0,
    )
    label_x = node_right + 3
    annotation_y = height + 1
    node_columns = [
        (node.x, node.x + node.width)
        for node in nodes
    ]

    for index, edge in enumerate(missing_edges):
        route_by_point = {
            (x, y): glyph
            for x, y, glyph in edge.route
        }
        safe_route_points = [
            (x, y, glyph)
            for (x, y), glyph in route_by_point.items()
            if _GLYPH_ROUTES.get(glyph)
            and (
                y >= node_bottom
                or all(not (left <= x < right) for left, right in node_columns)
            )
        ]
        if not safe_route_points:
            raise RuntimeError(
                f"cannot place route annotation for edge {edge.id!r}"
            )

        anchor_x, anchor_y, _ = max(
            safe_route_points,
            key=lambda point: (
                point[1] >= node_bottom,
                bool({"E", "W"} & _GLYPH_ROUTES.get(point[2], frozenset())),
                point[1],
                point[0],
            ),
        )
        label_y = annotation_y + index * 2
        if label_y <= anchor_y:
            label_y = anchor_y + 1

        def add_directions(
            point: tuple[int, int],
            directions: set[str],
        ) -> None:
            current = route_by_point.get(point, "")
            current_directions = _GLYPH_ROUTES.get(
                current,
                frozenset(),
            )
            route_by_point[point] = _ROUTE_GLYPHS.get(
                current_directions | directions,
                "─",
            )

        if label_y > anchor_y:
            add_directions((anchor_x, anchor_y), {"S"})
            for row in range(anchor_y + 1, label_y):
                route_by_point[(anchor_x, row)] = "│"
            add_directions((anchor_x, label_y), {"N", "E"})
        else:
            add_directions((anchor_x, anchor_y), {"E"})

        label_end = label_x + _display_width(edge.route_label) - 1
        for column in range(anchor_x + 1, label_end + 1):
            route_by_point[(column, label_y)] = "─"
        edge.route = [
            (x, y, glyph)
            for (x, y), glyph in sorted(
                route_by_point.items(),
                key=lambda item: (item[0][1], item[0][0]),
            )
        ]
        annotations[edge.id] = (label_x, label_y, edge.route_label)
        width = max(width, label_end + 2)
        height = max(height, label_y + 2)

    return annotations, width, height


def _diagram_edge_label(edge: DiagramEdge) -> str:
    if edge.flow_item:
        return f"{edge.label or edge.relation}: {edge.flow_item}"
    return edge.label or edge.relation


def _inspection_symbol_label(symbol: dict[str, Any]) -> str:
    label = f"{symbol.get('name', '')} [{symbol.get('kind', 'element').replace('_', ' ')}]"
    display_type = _display_type(symbol)
    if display_type:
        label += f" : {display_type}"
    return label


def _inspection_tree(
    root: dict[str, Any],
    symbols: list[dict[str, Any]],
    *,
    indent: str = "",
) -> tuple[list[str], set[str]]:
    lines = [indent + _inspection_symbol_label(root)]
    names = {str(root.get("name", ""))}
    visited = {_symbol_id(root)}

    def add_children(parent: dict[str, Any], prefix: str) -> None:
        children = [
            symbol
            for symbol in symbols
            if symbol.get("container") == parent.get("name")
            and symbol.get("file") == parent.get("file")
            and _symbol_id(symbol) not in visited
            and (
                not _ancestors(symbol)
                or not _ancestors(parent)
                or _ancestors(symbol) == (*_ancestors(parent), str(parent.get("name", "")))
            )
        ]
        children.sort(
            key=lambda symbol: (
                symbol.get("range", {}).get("line", 0),
                symbol.get("name", "").casefold(),
            )
        )
        for index, child in enumerate(children):
            visited.add(_symbol_id(child))
            names.add(str(child.get("name", "")))
            last = index == len(children) - 1
            branch = "└─ " if last else "├─ "
            child_prefix = "   " if last else "│  "
            lines.append(prefix + branch + _inspection_symbol_label(child))
            add_children(child, prefix + child_prefix)

    add_children(root, indent)
    return lines, names


def _inspection_relationship_lines(
    names: set[str],
    edges: list[dict[str, Any]],
    *,
    excluded: set[tuple[str, str, str]] | None = None,
) -> list[str]:
    excluded = excluded or set()
    relationships = []
    seen_details = set()
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        relation = edge.get("relation")
        if (
            not isinstance(source, str)
            or not isinstance(target, str)
            or not isinstance(relation, str)
            or relation.lower() == "contains"
            or (source not in names and target not in names)
        ):
            continue
        key = source, relation, target
        if key in excluded:
            continue
        label = edge.get("label")
        flow_item = edge.get("flow_item")
        source_feature = edge.get("source_feature")
        target_feature = edge.get("target_feature")
        detail_key = (
            *key,
            source_feature if isinstance(source_feature, str) else "",
            target_feature if isinstance(target_feature, str) else "",
            flow_item if isinstance(flow_item, str) else "",
            label if isinstance(label, str) else "",
        )
        if detail_key in seen_details:
            continue
        seen_details.add(detail_key)
        if isinstance(flow_item, str) and flow_item.strip():
            relation_label = f"{label or relation}: {flow_item}"
        else:
            relation_label = f"{label} / {relation}" if label else relation
        source_display = (
            f"{source}.{source_feature}"
            if isinstance(source_feature, str) and source_feature
            else source
        )
        target_display = (
            f"{target}.{target_feature}"
            if isinstance(target_feature, str) and target_feature
            else target
        )
        line = f"  {source_display} -[{relation_label}]-> {target_display}"
        relationships.append(
            (
                source.casefold(),
                relation.casefold(),
                target.casefold(),
                line.casefold(),
                line,
            )
        )
    return [entry[4] for entry in sorted(relationships)]


def _node_inspection(
    root: dict[str, Any],
    symbols: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> list[str]:
    tree, names = _inspection_tree(root, symbols)
    lines = [f"Element: {_inspection_symbol_label(root)}", "", "Projected features:"]
    lines.extend(tree[1:] or ["  (none projected)"])
    relationships = _inspection_relationship_lines(names, edges)
    if relationships:
        lines.extend(["", "Projected relationships:", *relationships])
    return lines


def _edge_inspection(
    edge: DiagramEdge,
    node_by_id: dict[str, DiagramNode],
    symbols: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
) -> list[str]:
    symbol_by_id = {_symbol_id(symbol): symbol for symbol in symbols}
    source_node = node_by_id[edge.source]
    target_node = node_by_id[edge.target]
    source_root = symbol_by_id.get(source_node.id)
    target_root = symbol_by_id.get(target_node.id)
    source_tree, source_names = (
        _inspection_tree(source_root, symbols)
        if source_root
        else ([source_node.name], {source_node.name})
    )
    target_tree, target_names = (
        _inspection_tree(target_root, symbols)
        if target_root
        else ([target_node.name], {target_node.name})
    )
    source_name = edge.source_display
    target_name = edge.target_display
    lines = [
        f"Edge: {source_name} -[{edge.label or edge.relation}]-> {target_name}",
    ]
    if edge.relation.lower() == "connect" and edge.label:
        lines.extend(["", f"Interface usage: {edge.label}"])
    lines.extend(["", "Source side:", *[f"  {line}" for line in source_tree]])
    lines.extend(["", "Target side:", *[f"  {line}" for line in target_tree]])

    connected_names = source_names | target_names
    flow_edges = [
        relationship
        for relationship in relationships
        if isinstance(relationship.get("relation"), str)
        and (
            "flow" in relationship["relation"].lower()
            or relationship["relation"].lower() in {"binding", "bind", "delegate"}
        )
        and (
            relationship.get("source") in connected_names
            or relationship.get("target") in connected_names
        )
    ]
    related_lines = _inspection_relationship_lines(
        connected_names,
        flow_edges,
    )
    if related_lines:
        lines.extend(["", "Projected flows and bindings:", *related_lines])
    else:
        lines.extend(["", "Projected flows and bindings:", "  (none projected)"])
    return lines


def _canvas_text(canvas: list[list[str]], x: int, y: int, text: str) -> None:
    for character in text:
        if 0 <= y < len(canvas) and 0 <= x < len(canvas[y]):
            canvas[y][x] = character
        character_width = max(1, _display_width(character))
        for continuation in range(1, character_width):
            if 0 <= y < len(canvas) and 0 <= x + continuation < len(canvas[y]):
                canvas[y][x + continuation] = ""
        x += character_width


def _put_route(canvas: list[list[str]], x: int, y: int, character: str) -> None:
    if not (0 <= y < len(canvas) and 0 <= x < len(canvas[y])):
        return
    current = canvas[y][x]
    if current in {" ", character, ""}:
        canvas[y][x] = character
    elif character in {"▶", "▲"}:
        canvas[y][x] = character
    else:
        current_directions = _GLYPH_ROUTES.get(current, frozenset())
        next_directions = _GLYPH_ROUTES.get(character, frozenset())
        combined = current_directions | next_directions
        if combined:
            canvas[y][x] = _ROUTE_GLYPHS.get(frozenset(combined), character)


def _node_rows(node: DiagramNode) -> tuple[list[str], int, list[int]]:
    content_width = node.width - 4
    inner = node.width - 2
    rows = ["┌" + "─" * (node.width - 2) + "┐"]
    for text in node.kind_lines:
        rows.append("│ " + text + " " * (content_width - _display_width(text)) + " │")
    name_offset = len(rows)
    for text in node.name_lines:
        rows.append("│ " + text + " " * (content_width - _display_width(text)) + " │")
    for text in node.type_lines:
        rows.append("│ " + text + " " * (content_width - _display_width(text)) + " │")
    feature_offsets = []
    if node.feature_lines:
        rows.append("├" + "─" * (node.width - 2) + "┤")
        for feature, lines in node.feature_lines:
            feature.line_index = len(rows)
            feature_offsets.append(feature.line_index)
            for text in lines:
                rows.append(
                    "│ "
                    + text
                    + " " * (content_width - _display_width(text))
                    + " │"
                )
    rows.append("└" + "─" * (node.width - 2) + "┘")
    assert all(_display_width(row) == node.width for row in rows)
    return rows, name_offset, feature_offsets


def _byte_column(line: str, display_column: int) -> int:
    byte_column = 1
    current_display = 1
    for character in line:
        width = max(1, _display_width(character))
        if display_column < current_display + width:
            return byte_column
        current_display += width
        byte_column += len(character.encode("utf-8"))
    return byte_column


def _canvas_byte_column(canvas_row: list[str], display_column: int) -> int:
    return 1 + sum(
        len(character.encode("utf-8"))
        for character in canvas_row[: display_column - 1]
        if character
    )


def _draw_nodes(
    canvas: list[list[str]],
    nodes: list[DiagramNode],
    canvas_start_line: int,
) -> list[dict[str, Any]]:
    node_metadata = []
    for node in nodes:
        rows, name_offset, _ = _node_rows(node)
        for row_index, row in enumerate(rows):
            _canvas_text(canvas, node.x, node.y + row_index, row)
        ports = []
        for feature in node.features:
            if feature.kind.lower() != "port_usage":
                continue
            feature_row_index = node.y + feature.line_index
            for side in sorted(feature.port_sides):
                marker_column = (
                    node.x if side == "left" else node.x + node.width - 1
                )
                canvas[feature_row_index][marker_column] = "●"
                ports.append(
                    {
                        "id": feature.id,
                        "name": feature.name,
                        "side": side,
                        "line": canvas_start_line + feature_row_index,
                        "display_col": marker_column + 1,
                        "col": _canvas_byte_column(
                            canvas[feature_row_index],
                            marker_column + 1,
                        ),
                    }
                )
        name_line = node.y + name_offset
        name_row = canvas[name_line]
        node_top = canvas_start_line + node.y
        left_byte = _canvas_byte_column(name_row, node.x + 1)
        right_byte = _canvas_byte_column(name_row, node.x + node.width)
        name_byte = _canvas_byte_column(name_row, node.x + 3)
        features = []
        for feature in node.features:
            feature_line = canvas_start_line + node.y + feature.line_index
            feature_row = canvas[node.y + feature.line_index]
            features.append(
                {
                    "id": feature.id,
                    "name": feature.name,
                    "kind": feature.kind,
                    "label": feature.label,
                    "line": feature_line,
                    "col": _canvas_byte_column(feature_row, node.x + 3),
                }
            )
        node_metadata.append(
            {
                "id": node.id,
                "name": node.name,
                "kind": node.kind,
                "display_type": node.display_type,
                "file": node.file,
                "container": node.container,
                "ancestors": list(node.ancestors),
                "line": canvas_start_line + name_line,
                "col": name_byte,
                "top": node_top,
                "bottom": node_top + len(rows) - 1,
                "left": node.x + 1,
                "right": node.x + node.width,
                "left_col": left_byte,
                "right_col": right_byte,
                "features": features,
                "ports": ports,
            }
        )
    return node_metadata


def _layout_graph(
    view: dict[str, Any],
    focus: str | None,
    depth: int,
    max_width: int | None,
) -> tuple[DiagramLayout, list[dict[str, Any]]]:
    symbols = list(view.get("nodes", []))
    presentation = view.get("presentation")
    if not isinstance(presentation, str):
        presentation = None
    if presentation == "state_transition":
        state_names = {
            symbol.get("name")
            for symbol in symbols
            if symbol.get("kind", "").lower() == "state_usage"
        }
        symbols = [
            symbol
            for symbol in symbols
            if _is_presentation_element(symbol, presentation, state_names)
        ]
    if presentation in _PRESENTATION_NODE_KINDS:
        symbols = [
            symbol
            for symbol in symbols
            if not _is_package(symbol)
            and not _is_definition(symbol)
            and _is_presentation_element(symbol, presentation)
        ]
    names = {symbol.get("name") for symbol in symbols}
    edges = [
        edge
        for edge in view.get("edges", [])
        if edge.get("source") in names and edge.get("target") in names
        and (
            presentation not in _PRESENTATION_RELATIONS
            or edge.get("relation") in _PRESENTATION_RELATIONS[presentation]
        )
    ]
    if focus and focus in names:
        focused_symbols = [
            symbol for symbol in symbols if symbol.get("name") == focus
        ]
        allowed = {focus}
        for symbol in focused_symbols:
            allowed.update(_ancestors(symbol))
        allowed.update(
            symbol.get("name")
            for symbol in symbols
            if symbol.get("container") == focus
        )
        frontier = {focus}
        frontier.update(
            symbol.get("name")
            for symbol in symbols
            if symbol.get("container") == focus
        )
        for _ in range(max(0, depth)):
            frontier_sources = set(frontier)
            frontier_sources.update(
                symbol.get("name")
                for symbol in symbols
                if symbol.get("container") in frontier
            )
            allowed.update(frontier_sources)
            next_frontier = {
                edge["target"]
                for edge in edges
                if edge.get("source") in frontier_sources and edge.get("target") not in allowed
            }
            allowed.update(next_frontier)
            frontier = next_frontier
        visible_containers = {
            symbol.get("name")
            for symbol in symbols
            if symbol.get("name") in allowed and not _is_package(symbol)
        }
        symbols = [
            symbol
            for symbol in symbols
            if symbol.get("name") in allowed
            or symbol.get("container") in visible_containers
        ]
        edges = [
            edge for edge in edges
            if edge.get("source") in allowed and edge.get("target") in allowed
        ]

    nodes, feature_owner = _build_diagram_nodes(symbols, edges, presentation)
    diagram_edges = _build_diagram_edges(
        symbols,
        edges,
        nodes,
        feature_owner,
        presentation,
    )
    _mark_interconnection_ports(nodes, diagram_edges, presentation)
    _assign_ranks(nodes, diagram_edges)
    max_content_width = (
        48
        if max_width is None
        else max(8, min(48, (max_width - 14) // 3 - 4))
    )
    _prepare_node_text(nodes, max_content_width)
    width, height = _position_nodes(nodes, diagram_edges, max_width)
    _route_edges(nodes, diagram_edges)
    return DiagramLayout(nodes, diagram_edges, width, height), symbols


def _simple_node_metadata(
    symbol: dict[str, Any],
    line: str,
    line_number: int,
    left: int,
    right: int,
) -> dict[str, Any]:
    return {
        "id": _symbol_id(symbol),
        "name": symbol.get("name", ""),
        "kind": symbol.get("kind", "element"),
        "display_type": _display_type(symbol),
        "file": symbol.get("file", ""),
        "container": symbol.get("container"),
        "ancestors": list(_ancestors(symbol)),
        "line": line_number,
        "col": _byte_column(line, left),
        "top": line_number,
        "bottom": line_number,
        "left": left,
        "right": right,
        "left_col": _byte_column(line, left),
        "right_col": _byte_column(line, right + 1) - 1,
        "features": [],
    }


def _edge_entries(
    edges: list[dict[str, Any]],
    symbols: list[dict[str, Any]],
    lines: list[str],
    max_width: int | None,
    node_metadata: list[dict[str, Any]] | None = None,
) -> tuple[list[str], list[dict[str, Any]], int]:
    names = {symbol.get("name") for symbol in symbols}
    valid_edges = [
        edge
        for edge in edges
        if edge.get("source") in names and edge.get("target") in names
    ]
    if not valid_edges:
        return lines, [], 0

    lines.extend(["", "Edges:"])
    edge_header_line = len(lines)
    entry_metadata = []
    width = max_width - 2 if max_width is not None else None
    symbols_by_name = {symbol.get("name"): symbol for symbol in symbols}
    layout_nodes_by_name = {
        node.get("name"): node for node in (node_metadata or [])
    }
    for edge in valid_edges:
        source = edge.get("source", "")
        target = edge.get("target", "")
        relation = edge.get("label") or edge.get("relation", "related")
        summary = f"- {source} -[{relation}]-> {target}"
        start_line = len(lines) + 1
        wrapped = (
            _wrap(summary[2:], width)
            if width is not None
            else [summary[2:]]
        )
        lines.extend(("- " if index == 0 else "  ") + line for index, line in enumerate(wrapped))
        source_symbol = symbols_by_name.get(source, {})
        target_symbol = symbols_by_name.get(target, {})
        entry_metadata.append(
            {
                "source": source,
                "target": target,
                "relation": edge.get("relation", "related"),
                "label": edge.get("label"),
                "line": start_line,
                "col": _byte_column(lines[start_line - 1], 3),
                "source_line": layout_nodes_by_name.get(source, {}).get(
                    "line",
                    source_symbol.get("range", {}).get("line", 0),
                ),
                "target_line": layout_nodes_by_name.get(target, {}).get(
                    "line",
                    target_symbol.get("range", {}).get("line", 0),
                ),
                "route_cells": [],
                "source_id": _symbol_id(source_symbol) if source_symbol else "",
                "target_id": _symbol_id(target_symbol) if target_symbol else "",
            }
        )
    return lines, entry_metadata, edge_header_line


def _simple_layout_data(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    lines: list[str],
    edge_header_line: int = 0,
    presentation: str | None = None,
) -> dict[str, Any]:
    return {
        "nodes": nodes,
        "edges": edges,
        "width": max((_display_width(line) for line in lines), default=0),
        "height": len(lines),
        "edge_header_line": edge_header_line,
        **({"presentation": presentation} if presentation else {}),
    }


def _render_browser_view(
    view: dict[str, Any],
    max_width: int | None,
) -> dict[str, Any]:
    symbols = list(view.get("nodes", []))
    width = max_width or 100
    title = str(view.get("title", "BrowserView"))
    lines = [
        *_wrap(title, width),
        *_wrap("Hierarchy of exposed model elements.", width),
        "",
    ]
    candidates = [
        symbol
        for symbol in symbols
        if not _is_package(symbol)
        and symbol.get("kind", "").lower() not in {"view", "view_usage"}
    ]
    children: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
    for symbol in candidates:
        parent_id = _parent_id(symbol, candidates)
        children[parent_id].append(symbol)
    for child_list in children.values():
        child_list.sort(
            key=lambda symbol: (
                symbol.get("range", {}).get("line", 0),
                symbol.get("name", "").casefold(),
            )
        )

    node_metadata = []
    visited: set[str] = set()

    def add_branch(symbol: dict[str, Any], level: int) -> None:
        symbol_id = _symbol_id(symbol)
        if symbol_id in visited:
            return
        visited.add(symbol_id)
        indent = "  " * min(level, 24)
        marker = "└─ " if level else "• "
        kind = symbol.get("kind", "element").replace("_", " ")
        type_name = _display_type(symbol)
        label = f"{symbol.get('name', '')} [{kind}]"
        if isinstance(type_name, str) and type_name:
            label += f" : {type_name}"
        source_line = symbol.get("range", {}).get("line", 0)
        if source_line:
            label += f" ({Path(symbol.get('file', '')).name}:{source_line})"
        prefix = indent + marker
        wrapped_label = _wrap(
            label,
            max(8, width - _display_width(prefix)),
        )
        wrapped = [
            prefix + wrapped_label[0],
            *(
                " " * _display_width(prefix) + continuation
                for continuation in wrapped_label[1:]
            ),
        ]
        start = len(lines) + 1
        lines.extend(wrapped)
        name_start = _display_width(prefix) + 1
        node_metadata.append(
            _simple_node_metadata(
                symbol,
                lines[start - 1],
                start,
                name_start,
                max(name_start, _display_width(lines[start - 1])),
            )
        )
        for child in children.get(symbol_id, []):
            add_branch(child, level + 1)

    for root in children.get(None, []):
        add_branch(root, 0)
    for symbol in candidates:
        if _symbol_id(symbol) not in visited:
            add_branch(symbol, 0)

    if len(visited) < len(candidates):
        lines.extend(["", f"Note: rendered {len(visited)} of {len(candidates)} elements."])
    issues = view.get("issues", [])
    for issue in issues:
        lines.extend(["", *_wrap(f"Note: {issue}", width)])
    return {
        "graph": "\n".join(lines),
        "layout": _simple_layout_data(
            node_metadata,
            [],
            lines,
            presentation="browser",
        ),
    }


def _render_grid_view(
    view: dict[str, Any],
    max_width: int | None,
) -> dict[str, Any]:
    symbols = sorted(
        view.get("nodes", []),
        key=lambda symbol: (
            symbol.get("range", {}).get("line", 0),
            symbol.get("name", "").casefold(),
        ),
    )
    edges = list(view.get("edges", []))
    width = max(40, max_width or 96)
    title = view.get("title", "GridView")
    name_width = min(
        22,
        max(8, max((_display_width(s.get("name", "")) for s in symbols), default=8)),
    )
    kind_width = min(
        18,
        max(6, max((_display_width(s.get("kind", "")) for s in symbols), default=6)),
    )
    type_width = min(
        18,
        max(
            6,
            max(
                (
                    _display_width(str(s.get("attributes", {}).get("diagramType", "")))
                    for s in symbols
                    if isinstance(s.get("attributes"), dict)
                ),
                default=6,
            ),
        ),
    )
    owner_width = min(
        16,
        max(
            5,
            max(
                (_display_width(str(s.get("container") or "")) for s in symbols),
                default=5,
            ),
        ),
    )
    include_relationship_column = width >= 52
    columns = [
        ("Element", name_width, 8),
        ("Kind", kind_width, 6),
        ("Type", type_width, 6),
        ("Owner", owner_width, 5),
    ]
    if include_relationship_column:
        columns.append(("Relations", 9, 9))
    available_content = width - (3 * len(columns) + 1)
    column_widths = [desired for _, desired, _ in columns]
    minimum_widths = [minimum for _, _, minimum in columns]
    while sum(column_widths) > available_content:
        shrinkable = [
            index
            for index, (current, minimum) in enumerate(
                zip(column_widths, minimum_widths)
            )
            if current > minimum
        ]
        if not shrinkable:
            break
        widest = max(shrinkable, key=lambda index: column_widths[index])
        column_widths[widest] -= 1
    columns = [
        (label, column_widths[index])
        for index, (label, _, _) in enumerate(columns)
    ]
    if include_relationship_column:
        column_widths[-1] = max(8, available_content - sum(column_widths[:-1]))
        columns[-1] = (columns[-1][0], column_widths[-1])
    separator = "+" + "+".join("-" * (column_width + 2) for _, column_width in columns) + "+"
    title_lines = [
        *_wrap(str(title), width),
        *_wrap("Exposed elements and their projected relationships.", width),
        "",
    ]
    lines = title_lines + [separator]
    header = "|" + "|".join(
        f" {label.ljust(column_width)} "
        for label, column_width in columns
    ) + "|"
    lines.extend([header, separator])
    node_metadata = []

    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        relation = edge.get("label") or edge.get("relation", "related")
        outgoing[edge.get("source", "")].append(
            f"{relation}: {edge.get('target', '')}"
        )
    for symbol in symbols:
        display_type = _display_type(symbol) or ""
        cells = [
            str(symbol.get("name", "")),
            str(symbol.get("kind", "")),
            str(display_type or ""),
            str(symbol.get("container") or ""),
        ]
        if include_relationship_column:
            cells.append("; ".join(outgoing.get(symbol.get("name", ""), [])))
        wrapped_cells = [
            _wrap(cell, column_width)
            for cell, (_, column_width) in zip(cells, columns)
        ]
        row_height = max(map(len, wrapped_cells), default=1)
        row_start = len(lines) + 1
        cell_left = 2
        for row_index in range(row_height):
            row_cells = [
                wrapped[row_index] if row_index < len(wrapped) else ""
                for wrapped in wrapped_cells
            ]
            lines.append(
                "|"
                + "|".join(
                    f" {cell.ljust(column_width)} "
                    for cell, (_, column_width) in zip(row_cells, columns)
                )
                + "|"
            )
        name_left = cell_left + 1
        node_metadata.append(
            _simple_node_metadata(
                symbol,
                lines[row_start - 1],
                row_start,
                name_left,
                name_left + min(
                    column_widths[0],
                    max(1, _display_width(cells[0])),
                ) - 1,
            )
        )
        lines.append(separator)
    lines = title_lines + lines[len(title_lines):]
    lines, edge_metadata, edge_header_line = _edge_entries(
        edges,
        symbols,
        lines,
        width,
        node_metadata,
    )
    for issue in view.get("issues", []):
        lines.extend(["", *_wrap(f"Note: {issue}", width)])
    return {
        "graph": "\n".join(lines),
        "layout": _simple_layout_data(
            node_metadata,
            edge_metadata,
            lines,
            edge_header_line,
            "grid",
        ),
    }


def _numeric_point(value: Any) -> tuple[float, ...] | None:
    if isinstance(value, dict):
        lowered = {str(key).lower(): item for key, item in value.items()}
        coordinates = [lowered.get(axis) for axis in ("x", "y", "z")]
        if coordinates[0] is None or coordinates[1] is None:
            return None
        value = coordinates[:3] if coordinates[2] is not None else coordinates[:2]
    if isinstance(value, (list, tuple)) and len(value) in {2, 3}:
        if all(
            isinstance(item, (int, float))
            and not isinstance(item, bool)
            and math.isfinite(item)
            for item in value
        ):
            return tuple(float(item) for item in value)
    return None


def _geometry_point(symbol: dict[str, Any]) -> tuple[float, ...] | None:
    attributes = symbol.get("attributes", {})
    if not isinstance(attributes, dict):
        return None
    for key in ("position", "coordinates", "location", "origin", "point"):
        point = _numeric_point(attributes.get(key))
        if point is not None:
            return point
        nested = attributes.get(key)
        if isinstance(nested, dict):
            for value_key in ("value", "coordinates", "position"):
                point = _numeric_point(nested.get(value_key))
                if point is not None:
                    return point
    return None


def _render_geometry_view(
    view: dict[str, Any],
    max_width: int | None,
) -> dict[str, Any]:
    symbols = sorted(
        view.get("nodes", []),
        key=lambda symbol: (
            symbol.get("range", {}).get("line", 0),
            symbol.get("name", "").casefold(),
        ),
    )
    points = {}
    for symbol in symbols:
        point = _geometry_point(symbol)
        if point is not None:
            points[_symbol_id(symbol)] = point
    title = str(view.get("title", "GeometryView"))
    width = max_width or 80
    lines = _wrap(title, width)
    node_metadata = []
    if points:
        coordinate_count = max(len(point) for point in points.values() if point)
        lines.extend(
            _wrap(
                "Orthographic point projections use numeric positions from the language-server projection.",
                width,
            )
        )
        plot_width = max(12, min(48, (max_width or 80) - 16))
        plot_height = 12

        def project(value: float, minimum: float, maximum: float, extent: int) -> int:
            if maximum == minimum:
                return extent // 2
            return round((value - minimum) / (maximum - minimum) * (extent - 1))

        projections = [("XY", 0, 1)]
        if coordinate_count == 3:
            projections.extend([("XZ", 0, 2), ("YZ", 1, 2)])
        point_characters = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for projection_name, horizontal_axis, vertical_axis in projections:
            projected_symbols = [
                symbol
                for symbol in symbols
                if (point := points.get(_symbol_id(symbol))) is not None
                and len(point) > max(horizontal_axis, vertical_axis)
            ]
            if not projected_symbols:
                lines.extend(
                    [
                        "",
                        f"{projection_name} projection unavailable: no elements "
                        "have both coordinates.",
                    ]
                )
                continue
            projected_points = [
                points[_symbol_id(symbol)] for symbol in projected_symbols
            ]
            x_values = [point[horizontal_axis] for point in projected_points]
            y_values = [point[vertical_axis] for point in projected_points]
            x_min, x_max = min(x_values), max(x_values)
            y_min, y_max = min(y_values), max(y_values)
            lines.extend(["", f"{projection_name} projection:"])
            projection_start_line = len(lines) + 1
            plotted: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
            for symbol in projected_symbols:
                point = points.get(_symbol_id(symbol))
                assert point is not None
                x = project(point[horizontal_axis], x_min, x_max, plot_width)
                y = plot_height - 1 - project(
                    point[vertical_axis],
                    y_min,
                    y_max,
                    plot_height,
                )
                plotted[(x, y)].append(symbol)
            canvas = [[" " for _ in range(plot_width)] for _ in range(plot_height)]
            projection_nodes = []
            for coordinate, overlapping in plotted.items():
                character = (
                    point_characters[len(projection_nodes) % len(point_characters)]
                    if len(overlapping) == 1
                    else "+"
                )
                x, y = coordinate
                canvas[y][x] = character
                y_value = y_max - (y_max - y_min) * y / (plot_height - 1)
                axis_prefix = f"{y_value:>8.3g} |"
                for symbol in overlapping:
                    point = points[_symbol_id(symbol)]
                    projection_nodes.append(
                        {
                            **_simple_node_metadata(
                                symbol,
                                axis_prefix + "".join(canvas[y]),
                                projection_start_line + y,
                                _display_width(axis_prefix) + x + 1,
                                _display_width(axis_prefix) + x + 1,
                            ),
                            "point": list(point),
                            "layout_point": [x, plot_height - 1 - y],
                            "overlapping": [item["name"] for item in overlapping],
                        }
                    )
            if projection_name == "XY":
                node_metadata = projection_nodes
            for row_index, row in enumerate(canvas):
                y_value = y_max - (y_max - y_min) * row_index / (plot_height - 1)
                lines.append(f"{y_value:>8.3g} |" + "".join(row))
            lines.append("         +" + "-" * plot_width)
            lines.append(
                f"           axis {projection_name[0]} = {x_min:g} .. {x_max:g}"
            )
        lines.extend(["", "Coordinates:"])
        for symbol in symbols:
            point = points.get(_symbol_id(symbol))
            if point is not None:
                values = ", ".join(f"{value:g}" for value in point)
                lines.append(f"- {symbol['name']} : ({values})")
            else:
                lines.append(f"- {symbol['name']} : position not projected")
                row_number = len(lines)
                row_text = lines[-1]
                node_metadata.append(
                    _simple_node_metadata(
                        symbol,
                        row_text,
                        row_number,
                        3,
                        max(3, _display_width(row_text)),
                    )
                )
    else:
        lines.extend(
            _wrap(
                "No numeric position attributes were included in the language-server projection.",
                width,
            )
            + _wrap(
                "Showing an element inventory; no spatial positions are inferred.",
                width,
            )
            + [""]
        )
        for symbol in symbols:
            attributes = symbol.get("attributes", {})
            details = []
            if isinstance(attributes, dict):
                for key, value in sorted(attributes.items()):
                    lowered = str(key).lower()
                    if any(
                        token in lowered
                        for token in ("position", "coordinate", "location", "origin", "shape")
                    ):
                        details.append(f"{key}={value}")
            label = f"- {symbol.get('name', '')} [{symbol.get('kind', 'element')}]"
            if details:
                label += " " + "; ".join(details)
            else:
                label += " (geometry data unavailable)"
            line_number = len(lines) + 1
            lines.append(label)
            node_metadata.append(
                _simple_node_metadata(
                    symbol,
                    label,
                    line_number,
                    3,
                    max(3, _display_width(label)),
                )
            )
    edges = []
    lines, edge_metadata, edge_header_line = _edge_entries(
        list(view.get("edges", [])),
        symbols,
        lines,
        max_width,
    )
    for issue in view.get("issues", []):
        lines.extend(["", *_wrap(f"Note: {issue}", max_width or 80)])
    return {
        "graph": "\n".join(lines),
        "layout": _simple_layout_data(
            node_metadata,
            edge_metadata,
            lines,
            edge_header_line,
            "geometry",
        ),
    }


def _render_sequence_view(
    view: dict[str, Any],
    max_width: int | None,
) -> dict[str, Any]:
    symbols = list(view.get("nodes", []))
    by_name = {symbol.get("name"): symbol for symbol in symbols}
    participants = [
        symbol
        for symbol in symbols
        if symbol.get("kind", "").lower()
        in {"part_usage", "actor_usage", "lifeline_usage"}
    ]
    if not participants:
        participants = [
            symbol
            for symbol in symbols
            if symbol.get("kind", "").lower() in {"action_usage", "item_usage"}
            and not symbol.get("container")
        ]
    participants.sort(
        key=lambda symbol: (
            symbol.get("range", {}).get("line", 0),
            symbol.get("name", "").casefold(),
        )
    )
    if not participants:
        fallback = _render_browser_view(
            {
                **view,
                "title": f"SequenceView [{view.get('title', '')}]",
                "issues": [
                    *view.get("issues", []),
                    "no exposed lifeline features were found; showing the model hierarchy",
                ],
            },
            max_width,
        )
        fallback["layout"]["presentation"] = "sequence"
        return fallback

    participant_by_name = {
        symbol["name"]: symbol for symbol in participants
    }
    participant_index_by_name = {
        symbol["name"]: index for index, symbol in enumerate(participants)
    }
    max_lane_width = max(
        12,
        min(
            30,
            ((max_width or 100) - 4) // max(1, len(participants)),
        ),
    )
    lane_widths = [
        min(
            max_lane_width,
            max(12, _display_width(symbol.get("name", "")) + 8),
        )
        for symbol in participants
    ]
    lane_starts = []
    cursor = 2
    for lane_width in lane_widths:
        lane_starts.append(cursor)
        cursor += lane_width
    lane_centers = [
        start + lane_width // 2
        for start, lane_width in zip(lane_starts, lane_widths)
    ]
    participant_by_id = {
        _symbol_id(symbol): index for index, symbol in enumerate(participants)
    }

    def participant_index(symbol: dict[str, Any] | None) -> int | None:
        if symbol is None:
            return None
        if symbol.get("name") in participant_by_name:
            return participant_index_by_name[symbol["name"]]
        ancestors = [*symbol.get("ancestors", ()), symbol.get("container")]
        for ancestor in reversed(ancestors):
            if ancestor in participant_by_name:
                return participant_index_by_name[ancestor]
        return None

    event_kinds = {
        "action_usage",
        "item_usage",
        "event_occurrence",
        "send_action_usage",
        "accept_action_usage",
        "flow_connection_usage",
    }
    timeline = []
    for symbol in symbols:
        kind = symbol.get("kind", "").lower()
        if kind not in event_kinds or symbol in participants:
            continue
        lane = participant_index(symbol)
        if lane is None:
            continue
        timeline.append(
            (
                symbol.get("range", {}).get("line", 0),
                0,
                "event",
                symbol,
                lane,
            )
        )

    relation_names = {
        "message",
        "send",
        "accept",
        "flow",
        "flow_connection",
        "succession",
        "connect",
    }
    for edge in view.get("edges", []):
        relation = str(edge.get("relation", "")).lower()
        if relation not in relation_names:
            continue
        source_symbol = by_name.get(edge.get("source"))
        target_symbol = by_name.get(edge.get("target"))
        source_lane = participant_index(source_symbol)
        target_lane = participant_index(target_symbol)
        if source_lane is None or target_lane is None:
            continue
        timeline.append(
            (
                edge.get("range", {}).get("line", 0),
                1,
                "message",
                edge,
                (source_lane, target_lane),
            )
        )
    timeline.sort(key=lambda entry: (entry[0], entry[1]))

    title = str(view.get("title", "SequenceView"))
    lines = [
        *_wrap(title, max_width or 100),
        *_wrap(
            "Time proceeds downward; exposed features are lifelines.",
            max_width or 100,
        ),
        "",
    ]
    header = [" " for _ in range(max(cursor + 2, max_width or 0))]
    for participant, start, lane_width in zip(participants, lane_starts, lane_widths):
        name = str(participant.get("name", ""))
        shown = name[: max(1, lane_width - 4)]
        _canvas_text([header], start, 0, f"┌─{shown}─┐")
    lines.append("".join(header).rstrip())
    lines.append("".join(
        " " * start + " " * max(0, lane_width // 2 - 1) + "│"
        for start, lane_width in zip(lane_starts, lane_widths)
    ).rstrip())
    node_metadata = []
    event_rows = []

    for _, _, entry_kind, entry, lane_info in timeline:
        row = [" " for _ in range(max(cursor + 2, max_width or 0))]
        for lane_center in lane_centers:
            if lane_center < len(row):
                row[lane_center] = "│"
        if entry_kind == "event":
            lane_index = lane_info
            center = lane_centers[lane_index]
            label = str(entry.get("name", "event"))
            start = lane_starts[lane_index]
            event_text = "● " + label[: max(4, lane_widths[lane_index] - 5)]
            event_start = max(start, center - 1)
            _canvas_text([row], event_start, 0, event_text)
            event_line = "".join(row).rstrip()
            node_metadata.append(
                _simple_node_metadata(
                    entry,
                    event_line,
                    len(lines) + 1,
                    event_start + 1,
                    event_start + _display_width(event_text),
                )
            )
            event_rows.append((entry, len(lines) + 1))
        else:
            source_lane, target_lane = lane_info
            start_x = lane_centers[source_lane]
            end_x = lane_centers[target_lane]
            relation_label = str(entry.get("label") or entry.get("relation", "message"))
            low, high = sorted((start_x, end_x))
            for x in range(low, high + 1):
                row[x] = "─"
            arrow = "▶" if end_x >= start_x else "◀"
            row[end_x] = arrow
            label = f"[{relation_label}]"
            available = max(0, high - low - 3)
            if available >= len(label):
                label_start = low + max(1, (high - low - len(label)) // 2)
                _canvas_text([row], label_start, 0, label)
            event_rows.append((entry, len(lines) + 1))
        lines.append("".join(row).rstrip())

    bottom_line = len(lines)
    for participant, start, lane_width in zip(participants, lane_starts, lane_widths):
        label_line = next(
            (
                line_index
                for line_index, line in enumerate(lines, 1)
                if participant.get("name", "") in line and line_index <= 4
            ),
            4,
        )
        node_metadata.append(
            {
                **_simple_node_metadata(
                    participant,
                    lines[label_line - 1],
                    label_line,
                    start + 2,
                    start + min(lane_width - 3, max(2, _display_width(participant["name"]) + 1)),
                ),
                "top": label_line,
                "bottom": max(label_line, bottom_line),
                "lane": participant.get("name"),
            }
        )
    lines.append("".join(
        " " * start + " " * max(0, lane_width // 2 - 1) + "│"
        for start, lane_width in zip(lane_starts, lane_widths)
    ).rstrip())

    layout_edges = []
    for entry, line_number in event_rows:
        if not isinstance(entry, dict) or "source" not in entry:
            continue
        source_lane = participant_index(by_name.get(entry.get("source")))
        target_lane = participant_index(by_name.get(entry.get("target")))
        if source_lane is None or target_lane is None:
            continue
        row = lines[line_number - 1]
        left, right = sorted((lane_centers[source_lane], lane_centers[target_lane]))
        layout_edges.append(
            {
                "source": entry.get("source", ""),
                "target": entry.get("target", ""),
                "relation": entry.get("relation", "message"),
                "label": entry.get("label"),
                "line": line_number,
                "col": _byte_column(row, left + 1),
                "source_line": line_number,
                "target_line": line_number,
                "route_cells": [
                    [line_number, _byte_column(row, column + 1)]
                    for column in range(left, right + 1)
                ],
                "source_id": _symbol_id(by_name.get(entry.get("source"), {})),
                "target_id": _symbol_id(by_name.get(entry.get("target"), {})),
                "source_node_id": _symbol_id(participants[source_lane]),
                "target_node_id": _symbol_id(participants[target_lane]),
            }
        )

    if not any(item[2] == "event" for item in timeline):
        lines.extend(["", "No event occurrences were projected for these lifelines."])
    lines, summary_edges, edge_header_line = _edge_entries(
        [edge for edge in view.get("edges", []) if edge.get("relation") in relation_names],
        symbols,
        lines,
        max_width,
        node_metadata,
    )
    routed_edges = {
        (edge["source"], edge["target"], edge["relation"]): edge
        for edge in layout_edges
    }
    for summary_edge in summary_edges:
        route = routed_edges.get(
            (
                summary_edge["source"],
                summary_edge["target"],
                summary_edge["relation"],
            )
        )
        if route:
            summary_edge.update(
                route_cells=route["route_cells"],
                source_line=route["source_line"],
                target_line=route["target_line"],
                source_node_id=route["source_node_id"],
                target_node_id=route["target_node_id"],
            )
    layout_edges = summary_edges
    for issue in view.get("issues", []):
        lines.extend(["", *_wrap(f"Note: {issue}", max_width or 100)])
    return {
        "graph": "\n".join(lines),
        "layout": _simple_layout_data(
            node_metadata,
            layout_edges,
            lines,
            edge_header_line,
            "sequence",
        ),
    }


def render_graph_data(
    view: dict[str, Any],
    focus: str | None = None,
    depth: int = 4,
    max_width: int | None = None,
) -> dict[str, Any]:
    presentation = view.get("presentation")
    if presentation == "browser":
        return _render_browser_view(view, max_width)
    if presentation == "grid":
        return _render_grid_view(view, max_width)
    if presentation == "geometry":
        return _render_geometry_view(view, max_width)
    if presentation == "sequence":
        return _render_sequence_view(view, max_width)

    layout, visible_symbols = _layout_graph(view, focus, depth, max_width)
    if not layout.nodes:
        title = view.get(
            "title",
            f"View Graph: {view.get('type', 'composition')} (structural diagram)",
        )
        notes = [f"Note: {issue}" for issue in view.get("issues", [])]
        return {
            "graph": (
                f"{title}\n\n(no visible model elements)"
                + ("\n" + "\n".join(notes) if notes else "")
            ),
            "layout": {
                "nodes": [],
                "edges": [],
                "width": 0,
                "height": 0,
                "presentation": presentation,
            },
        }
    title = view.get(
        "title",
        f"View Graph: {view.get('type', 'composition')} (structural diagram)",
    )
    legend_text = (
        "Parts are nodes; nested parts and ports are features; connectors join "
        "their owning parts at port features."
    )
    legend_texts = {
        "interconnection": legend_text,
        "action_flow": (
            "Actions are nodes; parameters are features; edges show projected "
            "flow, binding, and succession relationships."
        ),
        "state_transition": (
            "States are nodes; nested states are features; transitions are edges."
        ),
    }
    legend = legend_texts.get(
        presentation,
        "Feature rows show containment; arrows show relationships",
    )
    header_width = max_width or 100
    header_lines = [
        *_wrap(str(title), header_width),
        *_wrap(legend, header_width),
        "",
    ]
    route_annotations, layout.width, layout.height = _ensure_route_annotations(
        layout.nodes,
        layout.edges,
        layout.width,
        layout.height,
    )
    canvas_start_line = len(header_lines) + 1
    canvas = [[" " for _ in range(layout.width)] for _ in range(layout.height)]

    edge_route_metadata = []
    node_by_id = {node.id: node for node in layout.nodes}
    for edge in layout.edges:
        dash = edge.relation in {"dependency", "allocate", "import"}
        glyph_map = {"─": "┄", "│": "┆"} if dash else {}
        edge.route = [
            (x, y, glyph_map.get(character, character))
            for x, y, character in edge.route
        ]
    _mark_flow_routes(
        [
            edge
            for edge in layout.edges
            if edge.id not in route_annotations
            and edge.relation.lower()
            in {"flow", "flow_connection", "item_flow"}
        ]
    )
    for edge in layout.edges:
        for x, y, character in edge.route:
            _put_route(canvas, x, y, character)
    for x, y, label in route_annotations.values():
        _canvas_text(canvas, x, y, label)

    node_metadata = _draw_nodes(canvas, layout.nodes, canvas_start_line)
    visible_symbols_by_id = {
        _symbol_id(symbol): symbol
        for symbol in visible_symbols
    }
    for node_metadata_item in node_metadata:
        symbol = visible_symbols_by_id.get(node_metadata_item["id"])
        if symbol:
            node_metadata_item["inspection"] = _node_inspection(
                symbol,
                visible_symbols,
                view.get("edges", []),
            )
    canvas_lines = ["".join(row).rstrip() for row in canvas]
    while canvas_lines and not canvas_lines[-1]:
        canvas_lines.pop()
    lines = header_lines + canvas_lines

    edge_header_line = 0
    edge_entry_lines = []
    if layout.edges:
        lines.extend(["", "Edges:"])
        edge_header_line = len(lines)
        for edge in layout.edges:
            summary = (
                f"- {edge.source_display} -[{_diagram_edge_label(edge)}]-> "
                f"{edge.target_display}"
            )
            summary_width = max_width - 2 if max_width is not None else _display_width(summary)
            edge_entry_line = len(lines) + 1
            for line_index, summary_line in enumerate(_wrap(summary[2:], summary_width)):
                prefix = "- " if line_index == 0 else "  "
                lines.append(prefix + summary_line)
            edge_entry_lines.append(edge_entry_line)
            source_node = node_by_id[edge.source]
            target_node = node_by_id[edge.target]
            source_feature = next(
                (
                    feature
                    for feature in source_node.features
                    if feature.id == edge.source_feature
                ),
                None,
            )
            target_feature = next(
                (
                    feature
                    for feature in target_node.features
                    if feature.id == edge.target_feature
                ),
                None,
            )
            source_row = (
                source_node.y + 1 + len(source_node.kind_lines)
                if source_feature is None
                else source_feature.line_index + source_node.y
            )
            target_row = (
                target_feature.line_index + target_node.y
                if target_feature
                else target_node.y + 1 + len(target_node.kind_lines)
            )
            edge_route_metadata.append(
                {
                    "id": edge.id,
                    "source": source_feature.name if source_feature else source_node.name,
                    "target": (
                        target_feature.name if target_feature else target_node.name
                    ),
                    "source_display": edge.source_display,
                    "target_display": edge.target_display,
                    "source_feature": (
                        source_feature.name if source_feature else None
                    ),
                    "target_feature": (
                        target_feature.name if target_feature else None
                    ),
                    "relation": edge.relation,
                    "label": edge.label,
                    "flow_item": edge.flow_item,
                    "annotation": edge.route_label,
                    "inspection": _edge_inspection(
                        edge,
                        node_by_id,
                        visible_symbols,
                        view.get("edges", []),
                    ),
                    "line": edge_entry_line,
                    "col": _byte_column(summary, 3),
                    "source_line": canvas_start_line + source_row,
                    "target_line": canvas_start_line + target_row,
                    "route_cells": [
                        [canvas_start_line + y, x + 1]
                        for x, y, _ in edge.route
                    ],
                    "source_id": edge.source,
                    "target_id": edge.target,
                }
            )

    layout_data = {
        "nodes": node_metadata,
        "edges": edge_route_metadata,
        "width": layout.width,
        "height": layout.height,
        "edge_header_line": edge_header_line,
        **({"presentation": presentation} if presentation else {}),
    }
    return {"graph": "\n".join(lines), "layout": layout_data}
