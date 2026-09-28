from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .adapter import ParserBackendError, SysMLLspAdapter
from .diagram import render_graph_data
from .render import build_view, render_dot, render_graph, render_svg, render_text
from .workspace import WorkspaceIndex


def _json_out(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _load_index(path: str) -> WorkspaceIndex:
    root = Path(path).resolve()
    index = WorkspaceIndex(root)
    index.refresh()
    return index


def cmd_check(args: argparse.Namespace) -> int:
    index = _load_index(args.path)
    diagnostics = index.diagnostics()
    output = {"workspace": str(index.root), "diagnostics": diagnostics}
    _json_out(output)
    return 1 if any(d["severity"] == "error" for d in diagnostics) else 0


def cmd_symbols(args: argparse.Namespace) -> int:
    index = _load_index(args.path)
    _json_out(index.symbols(args.query))
    return 0


def cmd_definition(args: argparse.Namespace) -> int:
    index = _load_index(args.path)
    definition = index.definition(args.name)
    _json_out(definition or {})
    return 0 if definition else 2


def cmd_references(args: argparse.Namespace) -> int:
    index = _load_index(args.path)
    _json_out(index.references(args.name))
    return 0


def cmd_hover(args: argparse.Namespace) -> int:
    index = _load_index(args.path)
    _json_out(index.hover(args.name) or {})
    return 0


def cmd_completion(args: argparse.Namespace) -> int:
    index = _load_index(args.path)
    _json_out(index.completion(args.prefix))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    index = _load_index(args.path)
    _json_out(index.query(args.kind, args.name))
    return 0


def cmd_tree(args: argparse.Namespace) -> int:
    index = _load_index(args.path)
    _json_out(index.tree())
    return 0


def cmd_view(args: argparse.Namespace) -> int:
    index = _load_index(args.path)
    view = build_view(index, args.type, args.focus, args.depth)
    if args.format == "json":
        _json_out(view)
    elif args.format == "text":
        print(render_text(view))
    elif args.format == "dot":
        print(render_dot(view))
    elif args.format == "svg":
        print(render_svg(view))
    elif args.format == "graph":
        print(render_graph(view, args.focus, args.depth, args.width))
    elif args.format == "graph-json":
        _json_out(render_graph_data(view, args.focus, args.depth, args.width))
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    _json_out(WorkspaceIndex(Path(args.path)).health())
    return 0


def cmd_parser_status(_: argparse.Namespace) -> int:
    adapter = SysMLLspAdapter()
    _json_out(adapter.capabilities())
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sysml", description="SysML v2/KerML backend CLI")
    sub = p.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="validate model files")
    check.add_argument("path", nargs="?", default=".")
    check.set_defaults(func=cmd_check)

    symbols = sub.add_parser("symbols", help="list symbols")
    symbols.add_argument("path", nargs="?", default=".")
    symbols.add_argument("--query")
    symbols.set_defaults(func=cmd_symbols)

    definition = sub.add_parser("definition", help="find first definition")
    definition.add_argument("name")
    definition.add_argument("--path", default=".")
    definition.set_defaults(func=cmd_definition)

    refs = sub.add_parser("references", help="find references")
    refs.add_argument("name")
    refs.add_argument("--path", default=".")
    refs.set_defaults(func=cmd_references)

    hover = sub.add_parser("hover", help="hover info")
    hover.add_argument("name")
    hover.add_argument("--path", default=".")
    hover.set_defaults(func=cmd_hover)

    comp = sub.add_parser("completion", help="completion items")
    comp.add_argument("prefix")
    comp.add_argument("--path", default=".")
    comp.set_defaults(func=cmd_completion)

    query = sub.add_parser("query", help="semantic query")
    query.add_argument("kind")
    query.add_argument("--name")
    query.add_argument("--path", default=".")
    query.set_defaults(func=cmd_query)

    tree = sub.add_parser("tree", help="workspace structural tree")
    tree.add_argument("path", nargs="?", default=".")
    tree.set_defaults(func=cmd_tree)

    view = sub.add_parser("view", help="render semantic views")
    view.add_argument("type", choices=["package", "composition", "connections", "requirements", "traceability", "dependencies", "behavior", "state", "tree"])
    view.add_argument("--focus")
    view.add_argument("--depth", type=int, default=3)
    view.add_argument("--width", type=int, default=80)
    view.add_argument("--path", default=".")
    view.add_argument(
        "--format",
        choices=["text", "dot", "svg", "json", "graph", "graph-json"],
        default="text",
    )
    view.set_defaults(func=cmd_view)

    health = sub.add_parser("health", help="backend health report")
    health.add_argument("--path", default=".")
    health.set_defaults(func=cmd_health)

    parser_status = sub.add_parser(
        "parser-status",
        help="report configured SysML language-server capabilities",
    )
    parser_status.set_defaults(func=cmd_parser_status)

    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return int(args.func(args))
    except ParserBackendError as error:
        print(f"sysml: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
