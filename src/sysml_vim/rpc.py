from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from .render import build_view
from .workspace import WorkspaceIndex


def _result(id_value: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_value, "result": result}


def _error(id_value: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_value, "error": {"code": code, "message": message}}


def _handle(method: str, params: dict[str, Any]) -> Any:
    path = Path(params.get("path", ".")).resolve()
    index = WorkspaceIndex(path)
    index.refresh()

    if method == "check":
        return index.diagnostics()
    if method == "symbols":
        return index.symbols(params.get("query"))
    if method == "definition":
        return index.definition(params["name"])
    if method == "references":
        return index.references(params["name"])
    if method == "hover":
        return index.hover(params["name"])
    if method == "completion":
        return index.completion(params.get("prefix", ""))
    if method == "query":
        return index.query(params["kind"], params.get("name"))
    if method == "tree":
        return index.tree()
    if method == "view":
        return build_view(index, params["type"], params.get("focus"), int(params.get("depth", 3)))
    if method == "health":
        return index.health()
    if method == "shutdown":
        return {"ok": True, "shutdown": True}
    raise KeyError(f"Unknown method: {method}")


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            method = req["method"]
            params = req.get("params", {})
            resp = _result(req.get("id"), _handle(method, params))
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
            if method == "shutdown":
                return 0
        except KeyError as exc:
            sys.stdout.write(json.dumps(_error(req.get("id") if isinstance(req, dict) else None, -32601, str(exc))) + "\n")
            sys.stdout.flush()
        except Exception as exc:  # noqa: BLE001
            sys.stdout.write(json.dumps(_error(req.get("id") if isinstance(req, dict) else None, -32603, str(exc))) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
