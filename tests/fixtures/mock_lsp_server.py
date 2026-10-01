"""Canned LSP responses for exercising sysml-vim's protocol adapter."""

from __future__ import annotations

import json
from pathlib import Path
import re
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


def model_for(path: Path, version: int, source_text: str = "") -> dict[str, Any]:
    filename = path.name
    if filename == "vehicle.sysml":
        elements = [
            element(
                "Hklqswumzd",
                "package",
                0,
                0,
                12,
                1,
                children=[
                    element(
                        "Tegyxc",
                        "part def",
                        1,
                        2,
                        3,
                        3,
                        children=[
                            element(
                                "vebfom",
                                "port",
                                2,
                                4,
                                2,
                                26,
                                relationships=[relationship("typing", "vebfom", "Gkgsiimz")],
                            )
                        ],
                    ),
                    element(
                        "Ygkahzr",
                        "part def",
                        5,
                        2,
                        8,
                        3,
                        children=[
                            element(
                                "hxipof",
                                "part",
                                6,
                                4,
                                6,
                                24,
                                relationships=[relationship("typing", "hxipof", "Tegyxc")],
                            ),
                            element(
                                "fpzwr",
                                "part",
                                7,
                                4,
                                7,
                                22,
                                relationships=[relationship("typing", "fpzwr", "Moech")],
                            ),
                        ],
                    ),
                    element("Gkgsiimz", "port def", 10, 2, 10, 21),
                    element("Moech", "part def", 11, 2, 11, 20),
                ],
            )
        ]
        relationships = [
            relationship("typing", "vebfom", "Gkgsiimz"),
            relationship("typing", "hxipof", "Tegyxc"),
            relationship("typing", "fpzwr", "Moech"),
        ]
    elif filename == "links.sysml":
        elements = [
            element(
                "Wjhfgql",
                "package",
                0,
                0,
                8,
                1,
                children=[
                    element(
                        "Ygkahzr",
                        "import",
                        1,
                        2,
                        1,
                        38,
                        attributes={"qualifiedName": "Hklqswumzd::Ygkahzr"},
                    ),
                    element(
                        "Pxish",
                        "part def",
                        3,
                        2,
                        7,
                        3,
                        children=[
                            element(
                                "hcgg",
                                "part",
                                4,
                                4,
                                4,
                                23,
                                relationships=[relationship("typing", "hcgg", "Ygkahzr")],
                            ),
                            element("Ygkahzr", "allocation", 5, 4, 5, 29),
                            element("Ygkahzr", "dependency", 6, 4, 6, 37),
                        ],
                    ),
                ],
            )
        ]
        relationships = [
            relationship("typing", "hcgg", "Ygkahzr"),
            relationship("dependency", "Pxish", "Ygkahzr"),
        ]
    elif filename == "behavior.sysml":
        elements = [
            element(
                "Lturzrgrewi",
                "package",
                0,
                0,
                8,
                1,
                children=[
                    element(
                        "Fdopfyfvfw",
                        "part def",
                        1,
                        2,
                        4,
                        3,
                        children=[
                            element("Vter", "state def", 2, 4, 2, 19),
                            element("Kmizbu", "state def", 3, 4, 3, 21),
                        ],
                    ),
                    element("Thhat", "action def", 7, 2, 7, 19),
                ],
            )
        ]
        relationships = [relationship("transition", "Fdopfyfvfw", "Kmizbu")]
    elif filename == "standard_views.sysml":
        elements = [
            element(
                "Example",
                "package",
                0,
                0,
                7,
                1,
                children=[
                    element(
                        "bleTraceView",
                        "view",
                        1,
                        2,
                        1,
                        53,
                        attributes={
                            "partType": "SysML::BrowserView",
                            "exposeTargets": "Root",
                        },
                    ),
                    element(
                        "Root",
                        "part",
                        2,
                        2,
                        6,
                        3,
                        children=[
                            element(
                                "Child",
                                "part",
                                3,
                                4,
                                5,
                                5,
                                children=[
                                    element("Leaf", "part", 4, 6, 4, 16),
                                ],
                            ),
                        ],
                    ),
                ],
            )
        ]
        relationships = []
    elif filename == "requirements.sysml":
        elements = [
            element(
                "Mbugwy",
                "package",
                0,
                0,
                8,
                1,
                children=[
                    element("Sr", "requirement def", 1, 2, 1, 21),
                    element(
                        "Ewperodqqkkojjr",
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
            relationship("satisfy", "Ewperodqqkkojjr", "Sr"),
        ]
    elif filename == "bad.sysml":
        elements = [
            element(
                "Umgluz",
                "package",
                0,
                0,
                2,
                24,
                children=[
                    element(
                        "Hka",
                        "part def",
                        1,
                        2,
                        2,
                        24,
                        children=[
                            element(
                                "k",
                                "part",
                                2,
                                4,
                                2,
                                24,
                                relationships=[relationship("typing", "k", "Gzoyuduynsp")],
                            )
                        ],
                    )
                ],
            )
        ]
        relationships = [relationship("typing", "k", "Gzoyuduynsp")]
    else:
        elements = []
        relationships = []

    existing_names = set()
    pending_elements = list(elements)
    while pending_elements:
        model_element = pending_elements.pop()
        existing_names.add(model_element["name"])
        pending_elements.extend(model_element.get("children", []))
    for declaration in re.finditer(
        r"^\s*part def\s+([A-Za-z_]\w*)\s*;",
        source_text,
        re.MULTILINE,
    ):
        declaration_name = declaration.group(1)
        if declaration_name in existing_names:
            continue
        declaration_line = source_text.count("\n", 0, declaration.start())
        line_text = source_text.splitlines()[declaration_line]
        declaration_column = line_text.find(declaration_name)
        package_element = next(
            (
                model_element
                for model_element in elements
                if model_element["type"] == "package"
            ),
            None,
        )
        if package_element is not None:
            package_element["children"].append(
                element(
                    declaration_name,
                    "part def",
                    declaration_line,
                    max(0, declaration_column - 2),
                    declaration_line,
                    len(line_text),
                )
            )
            existing_names.add(declaration_name)

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


def diagnostics_for(path: Path, source_text: str = "") -> list[dict[str, Any]]:
    if "SYSML_VIM_UNSAVED_CHECK" in source_text:
        return [
            {
                "severity": 1,
                "range": source_range(0, 0, 0, 1),
                "message": "diagnostic from unsaved buffer",
                "source": "sysml-v2-lsp",
            }
        ]
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
        "Ygkahzr": [
            ("links.sysml", 1, 30, 7),
            ("links.sysml", 4, 15, 7),
            ("links.sysml", 5, 21, 7),
            ("links.sysml", 6, 29, 7),
        ],
        "Tegyxc": [("vehicle.sysml", 6, 17, 6)],
        "Moech": [("vehicle.sysml", 7, 16, 5)],
        "Gkgsiimz": [("vehicle.sysml", 2, 17, 8)],
        "Sr": [("requirements.sysml", 3, 24, 2)],
        "Kmizbu": [],
        "Gzoyuduynsp": [("bad.sysml", 2, 12, 10)],
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
                        "diagnostics": diagnostics_for(document_path, text),
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
                "result":                 model_for(
                    document_path,
                    document.get("version", 1),
                    document.get("text", ""),
                ),
            }
        )
    elif method == "textDocument/documentSymbol":
        document_uri = parameters.get("textDocument", {}).get("uri")
        document = documents.get(document_uri, {})
        document_path = Path(unquote(urlparse(document_uri).path))
        model_result = model_for(
            document_path,
            document.get("version", 1),
            document.get("text", ""),
        )
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
            model_result = model_for(
                document_path,
                document.get("version", 1),
                document.get("text", ""),
            )
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
