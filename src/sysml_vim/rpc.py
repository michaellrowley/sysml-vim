from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from .adapter import OfficialPilotAdapter
from .render import build_view, render_graph, render_text
from .workspace import WorkspaceIndex

_INDEX_CACHE: dict[str, WorkspaceIndex] = {}


def _result(id_value: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_value, "result": result}


def _error(id_value: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_value, "error": {"code": code, "message": message}}


def _index_for(path_value: str, force_refresh: bool = True) -> WorkspaceIndex:
    path = str(Path(path_value).resolve())
    if path not in _INDEX_CACHE:
        _INDEX_CACHE[path] = WorkspaceIndex(Path(path))
    index = _INDEX_CACHE[path]
    if force_refresh:
        index.refresh()
    return index


def _handle(method: str, params: dict[str, Any]) -> Any:
    path = str(Path(params.get("path", ".")).resolve())

    if method == "official_status":
        return OfficialPilotAdapter().capabilities()
    if method == "official":
        if "operation" not in params:
            raise ValueError("Missing required param: operation")
        adapter = OfficialPilotAdapter()
        payload = params.get("payload", {})
        return adapter.invoke(params["operation"], Path(path), payload)

    index = _index_for(path, force_refresh=bool(params.get("refresh", True)))

    if method == "check":
        return {"workspace": str(index.root), "diagnostics": index.diagnostics()}
    if method == "symbols":
        return index.symbols(params.get("query"))
    if method == "definition":
        if "name" not in params:
            raise ValueError("Missing required param: name")
        return index.definition(params["name"])
    if method == "references":
        if "name" not in params:
            raise ValueError("Missing required param: name")
        return index.references(params["name"])
    if method == "hover":
        if "name" not in params:
            raise ValueError("Missing required param: name")
        return index.hover(params["name"])
    if method == "completion":
        return index.completion(params.get("prefix", ""))
    if method == "query":
        if "kind" not in params:
            raise ValueError("Missing required param: kind")
        return index.query(params["kind"], params.get("name"))
    if method == "tree":
        return index.tree()
    if method == "view":
        if "type" not in params:
            raise ValueError("Missing required param: type")
        return build_view(index, params["type"], params.get("focus"), int(params.get("depth", 3)))
    if method == "view_text":
        if "type" not in params:
            raise ValueError("Missing required param: type")
        view = build_view(index, params["type"], params.get("focus"), int(params.get("depth", 3)))
        return {"text": render_text(view)}
    if method == "view_graph":
        view_type = params.get("type", "composition")
        view = build_view(index, view_type, params.get("focus"), int(params.get("depth", 4)))
        return {"graph": render_graph(view, params.get("focus"), int(params.get("depth", 4)))}
    if method == "health":
        health = index.health()
        health["official_adapter"] = OfficialPilotAdapter().capabilities()
        return health
    if method == "shutdown":
        return {"ok": True, "shutdown": True}
    raise LookupError(f"Unknown method: {method}")


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        req: dict[str, Any] | None = None
        try:
            req = json.loads(line)
            method = req["method"]
            params = req.get("params", {})
            resp = _result(req.get("id"), _handle(method, params))
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
            if method == "shutdown":
                return 0
        except LookupError as exc:
            sys.stdout.write(json.dumps(_error(req.get("id") if isinstance(req, dict) else None, -32601, str(exc))) + "\n")
            sys.stdout.flush()
        except ValueError as exc:
            sys.stdout.write(json.dumps(_error(req.get("id") if isinstance(req, dict) else None, -32602, str(exc))) + "\n")
            sys.stdout.flush()
        except Exception as exc:  # noqa: BLE001
            sys.stdout.write(json.dumps(_error(req.get("id") if isinstance(req, dict) else None, -32603, str(exc))) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
