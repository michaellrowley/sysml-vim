from __future__ import annotations

import atexit
from collections import defaultdict
import json
import os
from pathlib import Path
import shlex
import shutil
import threading
from typing import Any
from urllib.parse import unquote, urlparse

from .lsp_client import LanguageServerClient, LanguageServerError


class ParserBackendError(RuntimeError):
    """Raised when the configured SysML language server cannot answer."""


class SysMLLspAdapter:
    """Use the SysML v2 LSP for parsing, diagnostics, and model projections."""

    _sysml_standards = [
        "SysML v2 textual grammar derived from OMG KEBNF",
        "KerML textual grammar derived from OMG KEBNF",
    ]

    def __init__(self) -> None:
        self.server_path = self._configured_server_path()
        self.command_override = os.getenv("SYSML_LSP_COMMAND", "").strip()
        self._clients: dict[str, LanguageServerClient] = {}
        self._client_lock = threading.Lock()
        atexit.register(self.close)

    @staticmethod
    def _configured_server_path() -> Path | None:
        configured_path = os.getenv("SYSML_LSP_SERVER", "").strip()
        if configured_path:
            return Path(configured_path).expanduser().resolve()

        data_home = Path(
            os.getenv("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        ).expanduser()
        installed_server = (
            data_home
            / "sysml-vim"
            / "lsp"
            / "node_modules"
            / "sysml-v2-lsp"
            / "dist"
            / "server"
            / "server.js"
        )
        return installed_server

    @staticmethod
    def _package_version(server_path: Path | None) -> str:
        if server_path is None:
            return "unknown"
        package_file = server_path.parents[2] / "package.json"
        try:
            package_data = json.loads(package_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return "unknown"
        package_version = package_data.get("version")
        return package_version if isinstance(package_version, str) else "unknown"

    def _resolved_command(self) -> list[str]:
        if self.command_override:
            command_arguments = shlex.split(self.command_override)
            if not command_arguments:
                raise ParserBackendError("SYSML_LSP_COMMAND is empty after parsing")
            executable = shutil.which(command_arguments[0])
            if executable is None and not Path(command_arguments[0]).is_file():
                raise ParserBackendError(
                    f"language server command was not found: {command_arguments[0]}"
                )
            command_arguments[0] = executable or command_arguments[0]
            return command_arguments

        if self.server_path is None or not self.server_path.is_file():
            raise ParserBackendError(self._configuration_error())
        node_arguments = shlex.split(os.getenv("SYSML_NODE_COMMAND", "node"))
        if not node_arguments:
            raise ParserBackendError("SYSML_NODE_COMMAND is empty after parsing")
        node_executable = shutil.which(node_arguments[0])
        if node_executable is None:
            raise ParserBackendError("Node.js 20 or newer was not found on PATH")
        node_arguments[0] = node_executable
        return [*node_arguments, str(self.server_path), "--stdio"]

    def available(self) -> bool:
        try:
            self._resolved_command()
        except ParserBackendError:
            return False
        return True

    def mode(self) -> str:
        return "custom-command" if self.command_override else "stdio"

    def capabilities(self) -> dict[str, Any]:
        configured = self.available()
        return {
            "configured": configured,
            "mode": self.mode() if configured else "disabled",
            "expected_parser": "SysML v2 Language Server (ANTLR)",
            "version": self._package_version(self.server_path),
            "validation_scope": "language-server diagnostics; not Pilot-equivalent validation",
            "response_validated": False,
            "env": {
                "SYSML_LSP_SERVER": bool(os.getenv("SYSML_LSP_SERVER")),
                "SYSML_LSP_COMMAND": bool(self.command_override),
            },
            "notes": [
                "the server uses a grammar-derived parser and its own semantic checks",
                "grammar and semantic validation coverage are not a claim of full OMG conformance",
                "the persistent JSON-RPC backend reuses one language-server process per workspace",
            ],
        }

    @staticmethod
    def _configuration_error() -> str:
        return (
            "SysML v2 parsing is unavailable: install sysml-v2-lsp@0.31.0 and set "
            "SYSML_LSP_SERVER to its dist/server/server.js entry point. "
            "No local subset parser or fallback is provided."
        )

    def _client_for(self, workspace: Path) -> LanguageServerClient:
        workspace_root = workspace.resolve()
        if workspace_root.is_file():
            workspace_root = workspace_root.parent
        cache_key = str(workspace_root)
        with self._client_lock:
            client = self._clients.get(cache_key)
            if client is None:
                client = LanguageServerClient(
                    self._resolved_command(),
                    workspace_root,
                )
                self._clients[cache_key] = client
            return client

    def parse_workspace(
        self,
        workspace: Path,
        files: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Parse workspace documents and adapt the LSP model to sysml-vim's index."""
        try:
            client = self._client_for(workspace)
            projections = client.update_workspace(files)
            parser_metadata = {
                "name": "SysML v2 Language Server (ANTLR)",
                "version": self._package_version(self.server_path),
                "standards": list(self._sysml_standards),
                "validation_scope": "language-server syntax and semantic diagnostics",
            }
            projected_files = self._project_workspace(client, files, projections)
            return {"parser": parser_metadata, "files": projected_files}
        except (LanguageServerError, OSError, ValueError) as error:
            raise ParserBackendError(str(error)) from error

    def _project_workspace(
        self,
        client: LanguageServerClient,
        source_files: list[dict[str, str]],
        projections: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        projected_files: dict[str, dict[str, Any]] = {}
        elements_by_file: dict[str, list[dict[str, Any]]] = {}
        declarations_by_name: dict[str, list[tuple[str, dict[str, int]]]] = defaultdict(list)
        declaration_positions_by_name: dict[str, set[tuple[str, int, int]]] = defaultdict(set)
        relationship_candidates: list[dict[str, Any]] = []

        for source in source_files:
            source_path = str(Path(source["path"]).resolve())
            projection = projections.get(source_path)
            if not isinstance(projection, dict):
                raise ParserBackendError(
                    f"language server omitted the model projection for {source_path}"
                )
            model = projection.get("model")
            if not isinstance(model, dict):
                raise ParserBackendError(
                    f"language server returned an invalid model for {source_path}"
                )
            elements = model.get("elements")
            if not isinstance(elements, list):
                raise ParserBackendError(
                    f"language server returned invalid model elements for {source_path}"
                )
            document_symbols = projection.get("document_symbols", [])
            if not isinstance(document_symbols, list):
                raise ParserBackendError(
                    f"language server returned invalid document symbols for {source_path}"
                )

            document_symbol_index = self._document_symbol_index(document_symbols)
            file_symbols, flattened_elements = self._flatten_model_elements(
                source_path,
                source["text"],
                elements,
                document_symbol_index,
            )
            elements_by_file[source_path] = flattened_elements
            projected_files[source_path] = {
                "path": source_path,
                "symbols": file_symbols,
                "references": [],
                "diagnostics": self._project_diagnostics(
                    projection.get("diagnostics", []),
                    model.get("diagnostics", []),
                    source_path,
                ),
                "imports": [],
            }

            for symbol_record in file_symbols:
                symbol_line = symbol_record["range"]["line"] - 1
                symbol_column = symbol_record["range"]["col"]
                declarations_by_name[symbol_record["name"]].append(
                    (
                        projection["uri"],
                        {"line": symbol_line, "character": symbol_column},
                    )
                )
                declaration_positions_by_name[symbol_record["name"]].add(
                    (source_path, symbol_line, symbol_column)
                )

            relationship_candidates.extend(
                self._relationship_candidates(source_path, flattened_elements, model)
            )
            projected_files[source_path]["imports"] = self._imports_from_elements(
                flattened_elements
            )

        locations_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for target_name in sorted({item["target"] for item in relationship_candidates}):
            for document_uri, declaration_position in declarations_by_name.get(
                target_name, []
            ):
                locations = client.references(document_uri, declaration_position)
                for location in locations:
                    normalized_location = self._normalize_location(location)
                    if normalized_location is None:
                        continue
                    location_path, source_range = normalized_location
                    if (
                        location_path,
                        source_range["line"] - 1,
                        source_range["col"],
                    ) in declaration_positions_by_name[target_name]:
                        continue
                    location_record = {
                        "path": location_path,
                        "range": source_range,
                    }
                    if location_record not in locations_by_name[target_name]:
                        locations_by_name[target_name].append(location_record)

        for target_name, reference_locations in locations_by_name.items():
            candidates_by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for candidate in relationship_candidates:
                if candidate["target"] == target_name:
                    candidates_by_file[candidate["file"]].append(candidate)
            for location_record in reference_locations:
                source_path = location_record["path"]
                candidates = candidates_by_file.get(source_path, [])
                if not candidates:
                    continue
                matching_candidates = self._matching_relationships(
                    location_record["range"],
                    candidates,
                    elements_by_file.get(source_path, []),
                )
                for candidate, source_name in matching_candidates:
                    reference_record = {
                        "name": target_name,
                        "range": location_record["range"],
                        "relation": candidate["relation"],
                        "source": source_name,
                    }
                    references = projected_files[source_path]["references"]
                    if reference_record not in references:
                        references.append(reference_record)

        for projected_file in projected_files.values():
            projected_file["references"].sort(
                key=lambda reference: (
                    reference["range"]["line"],
                    reference["range"]["col"],
                    reference["name"],
                    reference["relation"],
                )
            )
        return list(projected_files.values())

    @staticmethod
    def _document_symbol_index(
        document_symbols: list[dict[str, Any]],
    ) -> dict[tuple[str, int], dict[str, int]]:
        indexed_symbols: dict[tuple[str, int], dict[str, int]] = {}
        pending_symbols = list(document_symbols)
        while pending_symbols:
            document_symbol = pending_symbols.pop()
            if not isinstance(document_symbol, dict):
                continue
            symbol_name = document_symbol.get("name")
            selection_range = document_symbol.get("selectionRange")
            start_position = (
                selection_range.get("start")
                if isinstance(selection_range, dict)
                else None
            )
            if (
                isinstance(symbol_name, str)
                and isinstance(start_position, dict)
                and isinstance(start_position.get("line"), int)
                and isinstance(start_position.get("character"), int)
            ):
                indexed_symbols[(symbol_name, start_position["line"])] = start_position
            children = document_symbol.get("children", [])
            if isinstance(children, list):
                pending_symbols.extend(children)
        return indexed_symbols

    @classmethod
    def _flatten_model_elements(
        cls,
        source_path: str,
        source_text: str,
        model_elements: list[Any],
        document_symbol_index: dict[tuple[str, int], dict[str, int]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        symbols: list[dict[str, Any]] = []
        flattened_elements: list[dict[str, Any]] = []
        source_lines = source_text.splitlines()

        def visit(
            model_element: Any,
            parent_name: str | None,
            ancestor_names: tuple[str, ...],
        ) -> None:
            if not isinstance(model_element, dict):
                raise ParserBackendError(
                    f"language server returned a non-object model element for {source_path}"
                )
            element_name = model_element.get("name")
            element_type = model_element.get("type")
            element_range = model_element.get("range")
            if (
                not isinstance(element_name, str)
                or not isinstance(element_type, str)
                or not isinstance(element_range, dict)
            ):
                raise ParserBackendError(
                    f"language server returned an incomplete model element for {source_path}"
                )
            converted_range = cls._convert_lsp_range(element_range)
            start_line = converted_range["line"] - 1
            element_record = {
                "file": source_path,
                "name": element_name,
                "kind": element_type,
                "range": converted_range,
                "container": parent_name,
                "ancestors": ancestor_names,
                "attributes": model_element.get("attributes", {}),
                "relationships": model_element.get("relationships", []),
                "element_range": element_range,
            }
            flattened_elements.append(element_record)

            if (
                element_name
                and element_name != "unnamed"
                and element_type.lower() not in {
                    "import",
                    "allocation",
                    "binding",
                    "dependency",
                    "satisfy",
                    "verify",
                    "transition",
                }
            ):
                selection_position = document_symbol_index.get(
                    (element_name, start_line)
                )
                if selection_position is not None:
                    end_position = {
                        "line": start_line,
                        "character": selection_position["character"]
                        + len(element_name),
                    }
                    symbol_range = {
                        "line": start_line + 1,
                        "col": selection_position["character"],
                        "end_col": end_position["character"],
                    }
                else:
                    symbol_range = converted_range
                signature = (
                    source_lines[start_line].strip()
                    if 0 <= start_line < len(source_lines)
                    else None
                )
                symbols.append(
                    {
                        "name": element_name,
                        "kind": cls._symbol_kind(element_type),
                        "range": symbol_range,
                        "container": parent_name,
                        "signature": signature or None,
                    }
                )

            child_elements = model_element.get("children", [])
            if not isinstance(child_elements, list):
                raise ParserBackendError(
                    f"language server returned invalid children for {element_name!r}"
                )
            next_ancestors = (
                (*ancestor_names, element_name)
                if element_name and element_name != "unnamed"
                else ancestor_names
            )
            for child_element in child_elements:
                visit(
                    child_element,
                    element_name if element_name and element_name != "unnamed" else parent_name,
                    next_ancestors,
                )

        for root_element in model_elements:
            visit(root_element, None, ())
        return symbols, flattened_elements

    @staticmethod
    def _normalize_relation_type(relation_type: str) -> str:
        relation_names = {
            "typing": "typed_by",
            "allocation": "allocate",
            "specialization": "specializes",
            "subsetting": "subsets",
            "redefinition": "redefines",
        }
        return relation_names.get(relation_type.lower(), relation_type.lower())

    @staticmethod
    def _symbol_kind(element_type: str) -> str:
        usage_kinds = {
            "action": "action_usage",
            "attribute": "attribute_usage",
            "item": "item_usage",
            "part": "part_usage",
            "port": "port_usage",
            "requirement": "requirement_usage",
            "state": "state_usage",
        }
        normalized_type = " ".join(element_type.lower().split())
        if normalized_type in usage_kinds:
            return usage_kinds[normalized_type]
        return "_".join(normalized_type.split())

    @classmethod
    def _relationship_candidates(
        cls,
        source_path: str,
        flattened_elements: list[dict[str, Any]],
        model: dict[str, Any],
    ) -> list[dict[str, Any]]:
        candidates_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}

        def add_candidate(
            relation_type: Any,
            source_name: Any,
            target_name: Any,
            range_hint: dict[str, Any] | None = None,
        ) -> None:
            if (
                not isinstance(relation_type, str)
                or not isinstance(target_name, str)
                or not target_name
            ):
                return
            target_short_name = target_name.split("::")[-1]
            normalized_source = source_name if isinstance(source_name, str) else ""
            normalized_relation = cls._normalize_relation_type(relation_type)
            candidate_key = (normalized_relation, normalized_source, target_short_name)
            existing_candidate = candidates_by_key.get(candidate_key)
            if existing_candidate is None or (
                existing_candidate.get("range_hint") is None and range_hint is not None
            ):
                candidates_by_key[candidate_key] = {
                    "file": source_path,
                    "relation": normalized_relation,
                    "source": normalized_source,
                    "target": target_short_name,
                    "range_hint": range_hint,
                }

        for element in flattened_elements:
            relationships = element.get("relationships", [])
            if isinstance(relationships, list):
                for relationship in relationships:
                    if isinstance(relationship, dict):
                        add_candidate(
                            relationship.get("type"),
                            relationship.get("source"),
                            relationship.get("target"),
                            element["element_range"],
                        )
            normalized_element_type = element["kind"].lower()
            if normalized_element_type in {"allocation", "import", "dependency"}:
                relationship_type = {
                    "allocation": "allocate",
                    "import": "import",
                    "dependency": "dependency",
                }[normalized_element_type]
                add_candidate(
                    relationship_type,
                    element.get("container"),
                    element["name"],
                    element["element_range"],
                )

        model_relationships = model.get("relationships", [])
        if not isinstance(model_relationships, list):
            raise ParserBackendError(
                f"language server returned invalid relationships for {source_path}"
            )
        for relationship in model_relationships:
            if not isinstance(relationship, dict):
                raise ParserBackendError(
                    f"language server returned an invalid relationship for {source_path}"
                )
            add_candidate(
                relationship.get("type"),
                relationship.get("source"),
                relationship.get("target"),
            )
        return list(candidates_by_key.values())

    @staticmethod
    def _imports_from_elements(flattened_elements: list[dict[str, Any]]) -> list[str]:
        imported_names: set[str] = set()
        for element in flattened_elements:
            if element["kind"].lower() != "import":
                continue
            attributes = element.get("attributes")
            imported_name: Any = element["name"]
            if isinstance(attributes, dict):
                for attribute_key in (
                    "qualifiedName",
                    "qualified_name",
                    "importedName",
                    "target",
                ):
                    if isinstance(attributes.get(attribute_key), str):
                        imported_name = attributes[attribute_key]
                        break
            if isinstance(imported_name, str) and imported_name:
                imported_names.add(imported_name)
        return sorted(imported_names)

    @classmethod
    def _matching_relationships(
        cls,
        reference_range: dict[str, int],
        candidates: list[dict[str, Any]],
        flattened_elements: list[dict[str, Any]],
    ) -> list[tuple[dict[str, Any], str | None]]:
        containing_elements = [
            element
            for element in flattened_elements
            if cls._range_contains(element["element_range"], reference_range)
        ]
        containing_elements.sort(
            key=lambda element: cls._range_size(element["element_range"])
        )
        containing_names = [
            name
            for element in containing_elements
            for name in (element["name"], *reversed(element["ancestors"]))
            if name and name != "unnamed"
        ]

        exact_candidates = [
            candidate
            for candidate in candidates
            if candidate.get("range_hint")
            and cls._range_contains(candidate["range_hint"], reference_range)
        ]
        if exact_candidates:
            return [
                (candidate, cls._display_relationship_source(candidate, containing_names))
                for candidate in exact_candidates
            ]

        source_candidates = [
            candidate
            for candidate in candidates
            if candidate["source"]
            and candidate["source"].lower() != "self"
            and candidate["source"] in containing_names
        ]
        if source_candidates:
            closest_source = min(
                source_candidates,
                key=lambda candidate: containing_names.index(candidate["source"]),
            )["source"]
            return [
                (candidate, candidate["source"])
                for candidate in source_candidates
                if candidate["source"] == closest_source
            ]

        self_candidates = [
            candidate
            for candidate in candidates
            if candidate["source"].lower() == "self"
        ]
        if self_candidates and containing_names:
            return [(self_candidates[0], containing_names[0])]
        return []

    @staticmethod
    def _display_relationship_source(
        candidate: dict[str, Any],
        containing_names: list[str],
    ) -> str | None:
        source_name = candidate["source"]
        if source_name and source_name.lower() != "self":
            return source_name
        return containing_names[0] if containing_names else None

    @staticmethod
    def _range_contains(
        container_range: dict[str, Any],
        location_range: dict[str, int],
    ) -> bool:
        start = container_range.get("start")
        end = container_range.get("end")
        if not isinstance(start, dict) or not isinstance(end, dict):
            return False
        location_start = (location_range["line"] - 1, location_range["col"])
        range_start = (start.get("line", -1), start.get("character", -1))
        range_end = (end.get("line", -1), end.get("character", -1))
        return range_start <= location_start <= range_end

    @staticmethod
    def _range_size(value: dict[str, Any]) -> int:
        start = value.get("start", {})
        end = value.get("end", {})
        start_line = start.get("line", 0)
        end_line = end.get("line", start_line)
        start_column = start.get("character", 0)
        end_column = end.get("character", start_column)
        return (end_line - start_line) * 1_000_000 + end_column - start_column

    @classmethod
    def _project_diagnostics(
        cls,
        language_server_diagnostics: Any,
        model_diagnostics: Any,
        source_path: str,
    ) -> list[dict[str, Any]]:
        if not isinstance(language_server_diagnostics, list):
            raise ParserBackendError(
                f"language server returned invalid diagnostics for {source_path}"
            )
        if not isinstance(model_diagnostics, list):
            raise ParserBackendError(
                f"language server returned invalid model diagnostics for {source_path}"
            )
        normalized_diagnostics: dict[tuple[Any, ...], dict[str, Any]] = {}
        severity_names = {1: "error", 2: "warning", 3: "info", 4: "info"}
        for diagnostic in [*language_server_diagnostics, *model_diagnostics]:
            if not isinstance(diagnostic, dict):
                raise ParserBackendError(
                    f"language server returned an invalid diagnostic for {source_path}"
                )
            severity = diagnostic.get("severity")
            if isinstance(severity, int):
                severity_name = severity_names.get(severity)
            else:
                severity_name = severity
            if severity_name not in {"error", "warning", "info"}:
                raise ParserBackendError(
                    f"language server returned unsupported diagnostic severity: {severity!r}"
                )
            message = diagnostic.get("message")
            if not isinstance(message, str) or not message:
                raise ParserBackendError(
                    f"language server returned a diagnostic without a message for {source_path}"
                )
            converted_range = cls._convert_lsp_range(diagnostic.get("range"))
            diagnostic_source = diagnostic.get("source")
            if not isinstance(diagnostic_source, str) or not diagnostic_source:
                diagnostic_source = "sysml-v2-lsp"
            normalized_diagnostic = {
                "range": converted_range,
                "severity": severity_name,
                "message": message,
                "source": diagnostic_source,
            }
            diagnostic_key = (
                converted_range["line"],
                converted_range["col"],
                converted_range["end_col"],
                severity_name,
                message,
            )
            normalized_diagnostics[diagnostic_key] = normalized_diagnostic
        return list(normalized_diagnostics.values())

    @staticmethod
    def _convert_lsp_range(value: Any) -> dict[str, int]:
        if not isinstance(value, dict):
            raise ParserBackendError("language server returned a source range that is not an object")
        start_position = value.get("start")
        end_position = value.get("end")
        if not isinstance(start_position, dict) or not isinstance(end_position, dict):
            raise ParserBackendError("language server returned an incomplete source range")
        coordinates = [
            start_position.get("line"),
            start_position.get("character"),
            end_position.get("line"),
            end_position.get("character"),
        ]
        if any(
            not isinstance(coordinate, int) or isinstance(coordinate, bool)
            for coordinate in coordinates
        ):
            raise ParserBackendError("language server returned non-integer source coordinates")
        start_line, start_column, end_line, end_column = coordinates
        if (
            start_line < 0
            or start_column < 0
            or end_line < start_line
            or end_column < 0
        ):
            raise ParserBackendError("language server returned an invalid source range")
        return {
            "line": start_line + 1,
            "col": start_column,
            "end_col": end_column,
        }

    @classmethod
    def _normalize_location(
        cls,
        location: dict[str, Any],
    ) -> tuple[str, dict[str, int]] | None:
        document_uri = location.get("uri")
        if not isinstance(document_uri, str):
            return None
        parsed_uri = urlparse(document_uri)
        if parsed_uri.scheme != "file":
            return None
        source_path = str(Path(unquote(parsed_uri.path)).resolve())
        source_range = cls._convert_lsp_range(location.get("range"))
        return source_path, source_range

    def close(self) -> None:
        with self._client_lock:
            clients = list(self._clients.values())
            self._clients.clear()
        for client in clients:
            client.close()
