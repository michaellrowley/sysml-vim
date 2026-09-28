from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
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


@dataclass(slots=True)
class DiagramNode:
    id: str
    name: str
    kind: str
    file: str
    source_line: int
    container: str | None
    ancestors: tuple[str, ...]
    features: list[DiagramFeature] = field(default_factory=list)
    kind_lines: list[str] = field(default_factory=list)
    name_lines: list[str] = field(default_factory=list)
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


def _ancestors(symbol: dict[str, Any]) -> tuple[str, ...]:
    values = symbol.get("ancestors", ())
    if isinstance(values, (list, tuple)):
        return tuple(value for value in values if isinstance(value, str))
    return ()


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
    direction = attributes.get("direction") if isinstance(attributes, dict) else None
    if isinstance(direction, str) and direction:
        return f"{direction} {name}"
    signature = symbol.get("signature")
    if isinstance(signature, str) and signature:
        return signature.strip().rstrip(";")
    return name


def _build_diagram_nodes(
    symbols: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> tuple[list[DiagramNode], dict[str, str]]:
    symbol_ids = {_symbol_id(symbol): symbol for symbol in symbols}
    candidates = [
        symbol
        for symbol in symbols
        if _is_definition(symbol) and not _is_package(symbol)
    ]
    for symbol in symbols:
        if _is_package(symbol) or _symbol_id(symbol) in {
            _symbol_id(candidate) for candidate in candidates
        }:
            continue
        if _parent_id(symbol, candidates) is None:
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
) -> list[DiagramEdge]:
    node_ids = {node.id for node in nodes}
    feature_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    symbol_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for symbol in symbols:
        symbol_by_name[symbol.get("name", "")].append(symbol)
        if _symbol_id(symbol) in feature_owner:
            feature_by_name[symbol.get("name", "")].append(symbol)

    diagram_edges = []
    seen: set[tuple[str, str, str, str | None]] = set()
    for edge in edges:
        relation = edge.get("relation")
        if not isinstance(relation, str) or relation == "contains":
            continue
        edge_line = edge.get("range", {}).get("line")
        edge_line = edge_line if isinstance(edge_line, int) else None
        source_symbol = _pick_symbol(
            feature_by_name.get(edge.get("source", ""), []),
            edge.get("source", ""),
            edge.get("file"),
            edge_line,
        )
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
        if source_symbol is None or target_symbol is None:
            continue

        source_id = _symbol_id(source_symbol)
        source_feature = source_id if source_id in feature_owner else None
        source_node = feature_owner.get(source_id, source_id)
        target_id = _symbol_id(target_symbol)
        target_node = feature_owner.get(target_id, target_id)
        if source_node not in node_ids or target_node not in node_ids or source_node == target_node:
            continue
        key = (source_node, target_node, relation, source_feature)
        if key in seen:
            continue
        seen.add(key)
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
                target_display=node_by_id[target_node].name,
                source_feature=source_feature,
            )
        )
    return diagram_edges


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
            [_display_width(node.name), _display_width(f"«{node.kind.replace('_', ' ')}»")]
            + [_display_width(label) for label in feature_labels],
            default=0,
        )
        content_width = min(max_content_width, max(8, longest))
        node.kind_lines = _wrap(f"«{node.kind.replace('_', ' ')}»", content_width)
        node.name_lines = _wrap(node.name, content_width)
        node.feature_lines = [
            (feature, _wrap(feature.label, content_width))
            for feature in node.features
        ]
        next_feature_line = 2 + len(node.kind_lines) + len(node.name_lines)
        for feature, lines in node.feature_lines:
            feature.line_index = next_feature_line
            next_feature_line += len(lines)
        node.width = content_width + 4
        node.height = (
            2
            + len(node.kind_lines)
            + len(node.name_lines)
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
    for edge in edges:
        source_rank = node_by_id[edge.source].rank
        target_rank = node_by_id[edge.target].rank
        if target_rank == source_rank + 1:
            edge_counts[(source_rank, target_rank)] += 1

    x_positions: dict[int, int] = {}
    x = 2
    if layers:
        max_rank = max(layers)
        for rank in range(max_rank + 1):
            x_positions[rank] = x
            x += rank_width.get(rank, 0)
            if rank < max_rank:
                count = edge_counts.get((rank, rank + 1), 0)
                x += max(8, count + 5) if max_width is None else count + 2

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
    for edge in edges:
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
            source_row = (
                source.y + feature_anchor[1].line_index
                if feature_anchor
                else source.y + 1 + len(source.kind_lines)
            )
            target_row = target.y + 1 + len(target.kind_lines)
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
        source_y = source.y + source.height
        target_y = target.y + target.height
        _add_route(
            edge,
            (source_x, source_y),
            (target_x, target_y),
            outer_y=outer_lane_y + index * 2,
        )


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
        name_line = node.y + name_offset
        name_row = rows[name_offset]
        node_top = canvas_start_line + node.y
        left_byte = node.x + _byte_column(name_row, 1)
        right_byte = node.x + _byte_column(name_row, node.width)
        name_byte = node.x + _byte_column(name_row, 3)
        features = []
        for feature in node.features:
            feature_line = canvas_start_line + node.y + feature.line_index
            feature_row = rows[feature.line_index]
            features.append(
                {
                    "id": feature.id,
                    "name": feature.name,
                    "kind": feature.kind,
                    "label": feature.label,
                    "line": feature_line,
                    "col": node.x + _byte_column(feature_row, 3),
                }
            )
        node_metadata.append(
            {
                "id": node.id,
                "name": node.name,
                "kind": node.kind,
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
    names = {symbol.get("name") for symbol in symbols}
    edges = [
        edge
        for edge in view.get("edges", [])
        if edge.get("source") in names and edge.get("target") in names
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

    nodes, feature_owner = _build_diagram_nodes(symbols, edges)
    diagram_edges = _build_diagram_edges(symbols, edges, nodes, feature_owner)
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


def render_graph_data(
    view: dict[str, Any],
    focus: str | None = None,
    depth: int = 4,
    max_width: int | None = None,
) -> dict[str, Any]:
    layout, _ = _layout_graph(view, focus, depth, max_width)
    if not layout.nodes:
        return {
            "graph": (
                f"View Graph: {view.get('type', 'composition')} "
                "(structural diagram)\n\n(no graph relationships)"
            ),
            "layout": {"nodes": [], "edges": [], "width": 0, "height": 0},
        }
    title = f"View Graph: {view.get('type', 'composition')} (structural diagram)"
    legend = ["Feature rows show containment; arrows show relationships"]
    header_lines = [title, legend[0], ""]
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
        for x, y, character in edge.route:
            _put_route(canvas, x, y, character)

    node_metadata = _draw_nodes(canvas, layout.nodes, canvas_start_line)
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
                f"- {edge.source_display} -[{edge.relation}]-> {edge.target_display}"
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
            source_row = (
                source_node.y + 1 + len(source_node.kind_lines)
                if source_feature is None
                else source_feature.line_index + source_node.y
            )
            target_row = target_node.y + 1 + len(target_node.kind_lines)
            edge_route_metadata.append(
                {
                    "source": source_feature.name if source_feature else source_node.name,
                    "target": target_node.name,
                    "relation": edge.relation,
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
    }
    return {"graph": "\n".join(lines), "layout": layout_data}
