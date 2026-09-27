from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

from .adapter import ParserBackendError, SysMLLspAdapter
from .render import build_view, render_graph, render_text
from .workspace import WorkspaceIndex

_INDEX_CACHE: dict[str, WorkspaceIndex] = {}


def _result(id_value: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_value, "result": result}


def _error(id_value: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_value, "error": {"code": code, "message": message}}


def _document_overrides(params: dict[str, Any]) -> dict[str, str]:
    document_records = params.get("documents", [])
    if not isinstance(document_records, list):
        raise ValueError("documents must be a list of path/text objects")

    document_overrides: dict[str, str] = {}
    for document_record in document_records:
        if not isinstance(document_record, dict):
            raise ValueError("each document override must be an object")
        document_path = document_record.get("path")
        document_text = document_record.get("text")
        if not isinstance(document_path, str) or not isinstance(document_text, str):
            raise ValueError("each document override requires string path and text fields")
        resolved_path = str(Path(document_path).expanduser().resolve())
        document_overrides[resolved_path] = document_text
    return document_overrides


def _index_for(
    path_value: str,
    force_refresh: bool = False,
    document_overrides: dict[str, str] | None = None,
) -> WorkspaceIndex:
    path = str(Path(path_value).resolve())
    if path not in _INDEX_CACHE:
        _INDEX_CACHE[path] = WorkspaceIndex(Path(path))
    index = _INDEX_CACHE[path]
    if force_refresh or not index.is_current(document_overrides):
        index.refresh(document_overrides)
    return index


def _handle(method: str, params: dict[str, Any]) -> Any:
    if method == "shutdown":
        return {"ok": True, "shutdown": True}

    path = str(Path(params.get("path", ".")).resolve())

    if method == "parser_status":
        return SysMLLspAdapter().capabilities()
    if method == "health":
        return WorkspaceIndex(Path(path)).health()

    index = _index_for(
        path,
        force_refresh=bool(params.get("refresh", False)),
        document_overrides=_document_overrides(params),
    )

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
                _close_workspace_indexes()
                return 0
        except LookupError as exc:
            sys.stdout.write(json.dumps(_error(req.get("id") if isinstance(req, dict) else None, -32601, str(exc))) + "\n")
            sys.stdout.flush()
        except ValueError as exc:
            sys.stdout.write(json.dumps(_error(req.get("id") if isinstance(req, dict) else None, -32602, str(exc))) + "\n")
            sys.stdout.flush()
        except ParserBackendError as exc:
            sys.stdout.write(json.dumps(_error(req.get("id") if isinstance(req, dict) else None, -32001, str(exc))) + "\n")
            sys.stdout.flush()
        except Exception as exc:  # noqa: BLE001
            sys.stdout.write(json.dumps(_error(req.get("id") if isinstance(req, dict) else None, -32603, str(exc))) + "\n")
            sys.stdout.flush()
    return 0


def _close_workspace_indexes() -> None:
    for workspace_index in _INDEX_CACHE.values():
        workspace_index.parser_adapter.close()
    _INDEX_CACHE.clear()


if __name__ == "__main__":
    raise SystemExit(main())
