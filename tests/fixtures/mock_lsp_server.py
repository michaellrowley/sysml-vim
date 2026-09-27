"""Canned LSP responses for exercising sysml-vim's protocol adapter."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse
from typing import Any


def source_range(
    start_line: int,
    start_column: int,
    end_line: int,
    end_column: int,
) -> dict[str, dict[str, int]]:
    return {
        "start": {"line": start_line, "character": start_column},
        "end": {"line": end_line, "character": end_column},
    }


def element(
    name: str,
    kind: str,
    start_line: int,
    start_column: int,
    end_line: int,
    end_column: int,
    *,
    children: list[dict[str, Any]] | None = None,
    attributes: dict[str, Any] | None = None,
    relationships: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "type": kind,
        "name": name,
        "range": source_range(start_line, start_column, end_line, end_column),
        "children": children or [],
        "attributes": attributes or {},
        "relationships": relationships or [],
    }


def relationship(kind: str, source: str, target: str) -> dict[str, str]:
    return {"type": kind, "source": source, "target": target}


def model_for(path: Path, version: int) -> dict[str, Any]:
    filename = path.name
    if filename == "vehicle.sysml":
        elements = [
            element(
                "VehiclePkg",
                "package",
                0,
                0,
                12,
                1,
                children=[
                    element(
                        "Engine",
                        "part def",
                        1,
                        2,
                        3,
                        3,
                        children=[
                            element(
                                "fuelIn",
                                "port",
                                2,
                                4,
                                2,
                                26,
                                relationships=[relationship("typing", "fuelIn", "FuelPort")],
                            )
                        ],
                    ),
                    element(
                        "Vehicle",
                        "part def",
                        5,
                        2,
                        8,
                        3,
                        children=[
                            element(
                                "engine",
                                "part",
                                6,
                                4,
                                6,
                                24,
                                relationships=[relationship("typing", "engine", "Engine")],
                            ),
                            element(
                                "wheel",
                                "part",
                                7,
                                4,
                                7,
                                22,
                                relationships=[relationship("typing", "wheel", "Wheel")],
                            ),
                        ],
                    ),
                    element("FuelPort", "port def", 10, 2, 10, 21),
                    element("Wheel", "part def", 11, 2, 11, 20),
                ],
            )
        ]
        relationships = [
            relationship("typing", "fuelIn", "FuelPort"),
            relationship("typing", "engine", "Engine"),
            relationship("typing", "wheel", "Wheel"),
        ]
    elif filename == "links.sysml":
        elements = [
            element(
                "LinkPkg",
                "package",
                0,
                0,
                8,
                1,
                children=[
                    element(
                        "Vehicle",
                        "import",
                        1,
                        2,
                        1,
                        38,
                        attributes={"qualifiedName": "VehiclePkg::Vehicle"},
                    ),
                    element(
                        "Fleet",
                        "part def",
                        3,
                        2,
                        7,
                        3,
                        children=[
                            element(
                                "lead",
                                "part",
                                4,
                                4,
                                4,
                                23,
                                relationships=[relationship("typing", "lead", "Vehicle")],
                            ),
                            element("Vehicle", "allocation", 5, 4, 5, 29),
                            element("Vehicle", "dependency", 6, 4, 6, 37),
                        ],
                    ),
                ],
            )
        ]
        relationships = [
            relationship("typing", "lead", "Vehicle"),
            relationship("dependency", "Fleet", "Vehicle"),
        ]
    elif filename == "behavior.sysml":
        elements = [
            element(
                "BehaviorPkg",
                "package",
                0,
                0,
                8,
                1,
                children=[
                    element(
                        "Controller",
                        "part def",
                        1,
                        2,
                        4,
                        3,
                        children=[
                            element("Idle", "state def", 2, 4, 2, 19),
                            element("Active", "state def", 3, 4, 3, 21),
                        ],
                    ),
                    element("Start", "action def", 7, 2, 7, 19),
                ],
            )
        ]
        relationships = [relationship("transition", "Controller", "Active")]
    elif filename == "requirements.sysml":
        elements = [
            element(
                "ReqPkg",
                "package",
                0,
                0,
                8,
                1,
                children=[
                    element("R1", "requirement def", 1, 2, 1, 21),
                    element(
                        "VerificationRig",
                        "part def",
                        2,
                        2,
                        4,
                        3,
                    ),
                ],
            )
        ]
        relationships = [
            relationship("satisfy", "VerificationRig", "R1"),
        ]
    elif filename == "bad.sysml":
        elements = [
            element(
                "Broken",
                "package",
                0,
                0,
                2,
                24,
                children=[
                    element(
                        "Bad",
                        "part def",
                        1,
                        2,
                        2,
                        24,
                        children=[
                            element(
                                "x",
                                "part",
                                2,
                                4,
                                2,
                                24,
                                relationships=[relationship("typing", "x", "MissingType")],
                            )
                        ],
                    )
                ],
            )
        ]
        relationships = [relationship("typing", "x", "MissingType")]
    else:
        elements = []
        relationships = []

    return {
        "version": version,
        "elements": elements,
        "relationships": relationships,
        "diagnostics": [],
    }


def document_symbols(model_elements: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    source_lines = text.splitlines()

    def convert(model_element: dict[str, Any]) -> dict[str, Any]:
        element_range = model_element["range"]
        start_position = element_range["start"]
        source_line = source_lines[start_position["line"]]
        selection_column = source_line.find(model_element["name"], start_position["character"])
        if selection_column < 0:
            selection_column = start_position["character"]
        selection_range = source_range(
            start_position["line"],
            selection_column,
            start_position["line"],
            selection_column + len(model_element["name"]),
        )
        return {
            "name": model_element["name"],
            "detail": model_element["type"],
            "kind": 5,
            "range": element_range,
            "selectionRange": selection_range,
            "children": [
                convert(child_element)
                for child_element in model_element.get("children", [])
                if child_element["type"] not in {"import", "allocation", "dependency"}
            ],
        }

    return [
        convert(model_element)
        for model_element in model_elements
        if model_element["type"] not in {"import", "allocation", "dependency"}
    ]


def send_message(message: dict[str, Any]) -> None:
    encoded_body = json.dumps(message, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(
        f"Content-Length: {len(encoded_body)}\r\n\r\n".encode("ascii")
        + encoded_body
    )
    sys.stdout.buffer.flush()


def read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        header_line = sys.stdin.buffer.readline()
        if not header_line:
            return None
        if header_line in {b"\r\n", b"\n"}:
            break
        header_name, separator, header_value = header_line.decode().partition(":")
        if separator:
            headers[header_name.strip().lower()] = header_value.strip()
    body = sys.stdin.buffer.read(int(headers["content-length"]))
    return json.loads(body.decode("utf-8"))


def diagnostics_for(path: Path) -> list[dict[str, Any]]:
    if path.name != "bad.sysml":
        return []
    return [
        {
            "severity": 1,
            "range": source_range(3, 0, 3, 5),
            "message": "extraneous input '<EOF>' while parsing a package",
            "source": "sysml-v2-lsp",
        }
    ]


def references_for(target_name: str) -> list[dict[str, Any]]:
    reference_locations = {
        "Vehicle": [
            ("links.sysml", 1, 30, 7),
            ("links.sysml", 4, 15, 7),
            ("links.sysml", 5, 21, 7),
            ("links.sysml", 6, 29, 7),
        ],
        "Engine": [("vehicle.sysml", 6, 17, 6)],
        "Wheel": [("vehicle.sysml", 7, 16, 5)],
        "FuelPort": [("vehicle.sysml", 2, 17, 8)],
        "R1": [("requirements.sysml", 3, 24, 2)],
        "Active": [],
        "MissingType": [("bad.sysml", 2, 12, 10)],
    }
    result = []
    for filename, line, column, token_length in reference_locations.get(target_name, []):
        matching_uri = next(
            (
                document_uri
                for document_uri in documents
                if Path(unquote(urlparse(document_uri).path)).name == filename
            ),
            None,
        )
        if matching_uri is None:
            continue
        result.append(
            {
                "uri": matching_uri,
                "range": source_range(line, column, line, column + token_length),
            }
        )
    return result


def find_document_symbol(
    document_symbols: list[dict[str, Any]],
    requested_position: dict[str, int],
) -> str | None:
    for document_symbol in document_symbols:
        if document_symbol["selectionRange"]["start"] == requested_position:
            return document_symbol["name"]
        nested_match = find_document_symbol(
            document_symbol.get("children", []),
            requested_position,
        )
        if nested_match is not None:
            return nested_match
    return None


documents: dict[str, dict[str, Any]] = {}

while True:
    request = read_message()
    if request is None:
        break
    method = request.get("method")
    parameters = request.get("params", {})
    request_id = request.get("id")

    if method == "initialize":
        send_message(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"capabilities": {"documentSymbolProvider": True}},
            }
        )
    elif method in {"textDocument/didOpen", "textDocument/didChange"}:
        document = parameters.get("textDocument", {})
        document_uri = document.get("uri")
        if method == "textDocument/didOpen":
            text = document.get("text", "")
        else:
            text = parameters.get("contentChanges", [{}])[-1].get("text", "")
        if isinstance(document_uri, str):
            documents[document_uri] = {
                "text": text,
                "version": document.get("version", 1),
            }
            document_path = Path(unquote(urlparse(document_uri).path))
            send_message(
                {
                    "jsonrpc": "2.0",
                    "method": "textDocument/publishDiagnostics",
                    "params": {
                        "uri": document_uri,
                        "diagnostics": diagnostics_for(document_path),
                    },
                }
            )
    elif method == "textDocument/didClose":
        document_uri = parameters.get("textDocument", {}).get("uri")
        documents.pop(document_uri, None)
    elif method == "sysml/model":
        document_uri = parameters.get("textDocument", {}).get("uri")
        document = documents.get(document_uri, {})
        document_path = Path(unquote(urlparse(document_uri).path))
        send_message(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": model_for(document_path, document.get("version", 1)),
            }
        )
    elif method == "textDocument/documentSymbol":
        document_uri = parameters.get("textDocument", {}).get("uri")
        document = documents.get(document_uri, {})
        document_path = Path(unquote(urlparse(document_uri).path))
        model_result = model_for(document_path, document.get("version", 1))
        send_message(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": document_symbols(model_result["elements"], document.get("text", "")),
            }
        )
    elif method == "textDocument/references":
        document_uri = parameters.get("textDocument", {}).get("uri")
        position = parameters.get("position", {})
        target_name = None
        for candidate_uri, document in documents.items():
            document_path = Path(unquote(urlparse(candidate_uri).path))
            model_result = model_for(document_path, document.get("version", 1))
            symbols = document_symbols(model_result["elements"], document.get("text", ""))
            if candidate_uri == document_uri:
                target_name = find_document_symbol(symbols, position)
        send_message(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": references_for(target_name) if target_name else [],
            }
        )
    elif method == "shutdown":
        send_message({"jsonrpc": "2.0", "id": request_id, "result": None})
    elif method == "exit":
        break
    elif request_id is not None:
        send_message(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"unsupported method: {method}"},
            }
        )
