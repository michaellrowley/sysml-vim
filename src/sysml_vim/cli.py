from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .adapter import OfficialPilotAdapter
from .render import build_view, render_dot, render_svg, render_text
from .workspace import WorkspaceIndex


def _json_out(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _load_index(path: str) -> WorkspaceIndex:
    root = Path(path).resolve()
    index = WorkspaceIndex(root)
    index.refresh()
    return index


def _maybe_official(args: argparse.Namespace, operation: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    if not getattr(args, "official", False):
        return None
    adapter = OfficialPilotAdapter()
    result = adapter.invoke(operation, Path(args.path).resolve(), payload)
    if result.get("ok"):
        return {
            "mode": "official",
            "adapter_mode": result.get("mode"),
            "operation": operation,
            "result": result.get("result"),
        }
    return {
        "mode": "local_fallback",
        "operation": operation,
        "official_error": result,
    }


def cmd_check(args: argparse.Namespace) -> int:
    official = _maybe_official(args, "check", {})
    if official and official["mode"] == "official":
        _json_out(official)
        return 0

    index = _load_index(args.path)
    diagnostics = index.diagnostics()
    output = {"workspace": str(index.root), "diagnostics": diagnostics}
    if official:
        output["official"] = official["official_error"]
    _json_out(output)
    return 1 if any(d["severity"] == "error" for d in diagnostics) else 0


def cmd_symbols(args: argparse.Namespace) -> int:
    official = _maybe_official(args, "symbols", {"query": args.query} if args.query else {})
    if official and official["mode"] == "official":
        _json_out(official)
        return 0

    index = _load_index(args.path)
    output: Any = index.symbols(args.query)
    if official:
        output = {"items": output, "official": official["official_error"]}
    _json_out(output)
    return 0


def cmd_definition(args: argparse.Namespace) -> int:
    official = _maybe_official(args, "definition", {"name": args.name})
    if official and official["mode"] == "official":
        _json_out(official)
        return 0

    index = _load_index(args.path)
    definition = index.definition(args.name)
    output: Any = definition or {}
    if official:
        output = {"item": output, "official": official["official_error"]}
    _json_out(output)
    return 0 if definition else 2


def cmd_references(args: argparse.Namespace) -> int:
    official = _maybe_official(args, "references", {"name": args.name})
    if official and official["mode"] == "official":
        _json_out(official)
        return 0

    index = _load_index(args.path)
    output: Any = index.references(args.name)
    if official:
        output = {"items": output, "official": official["official_error"]}
    _json_out(output)
    return 0


def cmd_hover(args: argparse.Namespace) -> int:
    official = _maybe_official(args, "hover", {"name": args.name})
    if official and official["mode"] == "official":
        _json_out(official)
        return 0

    index = _load_index(args.path)
    output: Any = index.hover(args.name) or {}
    if official:
        output = {"item": output, "official": official["official_error"]}
    _json_out(output)
    return 0


def cmd_completion(args: argparse.Namespace) -> int:
    official = _maybe_official(args, "completion", {"prefix": args.prefix})
    if official and official["mode"] == "official":
        _json_out(official)
        return 0

    index = _load_index(args.path)
    output: Any = index.completion(args.prefix)
    if official:
        output = {"items": output, "official": official["official_error"]}
    _json_out(output)
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    payload = {"kind": args.kind}
    if args.name:
        payload["name"] = args.name
    official = _maybe_official(args, "query", payload)
    if official and official["mode"] == "official":
        _json_out(official)
        return 0

    index = _load_index(args.path)
    output: Any = index.query(args.kind, args.name)
    if official:
        output = {"items": output, "official": official["official_error"]}
    _json_out(output)
    return 0


def cmd_tree(args: argparse.Namespace) -> int:
    official = _maybe_official(args, "tree", {})
    if official and official["mode"] == "official":
        _json_out(official)
        return 0

    index = _load_index(args.path)
    output: Any = index.tree()
    if official:
        output = {"tree": output, "official": official["official_error"]}
    _json_out(output)
    return 0


def cmd_view(args: argparse.Namespace) -> int:
    payload = {"type": args.type, "depth": args.depth}
    if args.focus:
        payload["focus"] = args.focus
    official = _maybe_official(args, "view", payload)
    if official and official["mode"] == "official":
        _json_out(official)
        return 0

    index = _load_index(args.path)
    view = build_view(index, args.type, args.focus, args.depth)
    if args.format == "json":
        out: Any = view
        if official:
            out = {"view": out, "official": official["official_error"]}
        _json_out(out)
    elif args.format == "text":
        print(render_text(view))
    elif args.format == "dot":
        print(render_dot(view))
    elif args.format == "svg":
        print(render_svg(view))
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    index = _load_index(args.path)
    adapter = OfficialPilotAdapter()
    health = index.health()
    health["official_adapter"] = adapter.capabilities()
    health["official_adapter"]["env_var"] = "SYSML_PILOT_COMMAND | SYSML_PILOT_RPC_COMMAND"
    _json_out(health)
    return 0


def cmd_adapter(args: argparse.Namespace) -> int:
    adapter = OfficialPilotAdapter()
    payload = json.loads(args.payload) if args.payload else {}
    result = adapter.invoke(args.operation, Path(args.path), payload)
    _json_out(result)
    return 0 if result.get("ok") else 2


def cmd_official_status(_: argparse.Namespace) -> int:
    adapter = OfficialPilotAdapter()
    _json_out(adapter.capabilities())
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sysml", description="SysML v2/KerML backend CLI")
    sub = p.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="validate model files")
    check.add_argument("path", nargs="?", default=".")
    check.add_argument("--official", action="store_true", help="try configured official adapter first")
    check.set_defaults(func=cmd_check)

    symbols = sub.add_parser("symbols", help="list symbols")
    symbols.add_argument("path", nargs="?", default=".")
    symbols.add_argument("--query")
    symbols.add_argument("--official", action="store_true", help="try configured official adapter first")
    symbols.set_defaults(func=cmd_symbols)

    definition = sub.add_parser("definition", help="find first definition")
    definition.add_argument("name")
    definition.add_argument("--path", default=".")
    definition.add_argument("--official", action="store_true", help="try configured official adapter first")
    definition.set_defaults(func=cmd_definition)

    refs = sub.add_parser("references", help="find references")
    refs.add_argument("name")
    refs.add_argument("--path", default=".")
    refs.add_argument("--official", action="store_true", help="try configured official adapter first")
    refs.set_defaults(func=cmd_references)

    hover = sub.add_parser("hover", help="hover info")
    hover.add_argument("name")
    hover.add_argument("--path", default=".")
    hover.add_argument("--official", action="store_true", help="try configured official adapter first")
    hover.set_defaults(func=cmd_hover)

    comp = sub.add_parser("completion", help="completion items")
    comp.add_argument("prefix")
    comp.add_argument("--path", default=".")
    comp.add_argument("--official", action="store_true", help="try configured official adapter first")
    comp.set_defaults(func=cmd_completion)

    query = sub.add_parser("query", help="semantic query")
    query.add_argument("kind")
    query.add_argument("--name")
    query.add_argument("--path", default=".")
    query.add_argument("--official", action="store_true", help="try configured official adapter first")
    query.set_defaults(func=cmd_query)

    tree = sub.add_parser("tree", help="workspace structural tree")
    tree.add_argument("path", nargs="?", default=".")
    tree.add_argument("--official", action="store_true", help="try configured official adapter first")
    tree.set_defaults(func=cmd_tree)

    view = sub.add_parser("view", help="render semantic views")
    view.add_argument("type", choices=["package", "composition", "connections", "requirements", "traceability", "dependencies", "behavior", "state", "tree"])
    view.add_argument("--focus")
    view.add_argument("--depth", type=int, default=3)
    view.add_argument("--path", default=".")
    view.add_argument("--format", choices=["text", "dot", "svg", "json"], default="text")
    view.add_argument("--official", action="store_true", help="try configured official adapter first")
    view.set_defaults(func=cmd_view)

    health = sub.add_parser("health", help="backend health report")
    health.add_argument("--path", default=".")
    health.set_defaults(func=cmd_health)

    official_status = sub.add_parser("official-status", help="report configured official adapter capabilities")
    official_status.set_defaults(func=cmd_official_status)

    adapter = sub.add_parser("adapter", help="invoke official adapter")
    adapter.add_argument("operation")
    adapter.add_argument("--path", default=".")
    adapter.add_argument("--payload")
    adapter.set_defaults(func=cmd_adapter)

    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
