from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import shutil
from typing import Any, Mapping

from .adapter import ParserBackendError, SysMLLspAdapter
from .model import Diagnostic, ParsedFile, Range, Reference, Symbol, iter_model_files


class WorkspaceIndex:
    def __init__(self, root: Path, parser_adapter: SysMLLspAdapter | None = None):
        self.root = root.resolve()
        self.parser_adapter = (
            parser_adapter if parser_adapter is not None else SysMLLspAdapter()
        )
        self.files: dict[str, ParsedFile] = {}
        self.symbols_by_name: dict[str, list[Symbol]] = {}
        self.references_by_name: dict[str, list[Reference]] = {}
        self.parser_info: dict[str, Any] = {}
        self.source_snapshot: dict[str, tuple[int, int]] = {}

    def refresh(self) -> None:
        self.files.clear()
        self.symbols_by_name.clear()
        self.references_by_name.clear()
        self.parser_info.clear()
        self.source_snapshot.clear()

        source_files = list(iter_model_files(self.root))
        parser_inputs = []
        source_snapshot = {}
        for source_file in source_files:
            try:
                file_stat = source_file.stat()
                source_text = source_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                raise ParserBackendError(f"Unable to read model file {source_file}: {error}") from error
            resolved_path = str(source_file.resolve())
            parser_inputs.append({"path": resolved_path, "text": source_text})
            source_snapshot[resolved_path] = (file_stat.st_mtime_ns, file_stat.st_size)

        parser_response = self.parser_adapter.parse_workspace(self.root, parser_inputs)
        self.parser_info, parsed_files = self._parse_response(parser_response, parser_inputs)
        self.files = {parsed.path: parsed for parsed in parsed_files}
        self.source_snapshot = source_snapshot
        for parsed in self.files.values():
            for symbol in parsed.symbols:
                self.symbols_by_name.setdefault(symbol.name, []).append(symbol)
            for reference in parsed.references:
                self.references_by_name.setdefault(reference.name, []).append(reference)

    def is_current(self) -> bool:
        current_snapshot = {}
        for source_file in iter_model_files(self.root):
            try:
                file_stat = source_file.stat()
            except OSError as error:
                raise ParserBackendError(f"Unable to inspect model file {source_file}: {error}") from error
            current_snapshot[str(source_file.resolve())] = (
                file_stat.st_mtime_ns,
                file_stat.st_size,
            )
        return current_snapshot == self.source_snapshot and bool(self.parser_info)

    def _parse_response(
        self,
        response: dict[str, Any],
        parser_inputs: list[dict[str, str]],
    ) -> tuple[dict[str, Any], list[ParsedFile]]:
        parser_info = response.get("parser")
        if not isinstance(parser_info, dict):
            raise ParserBackendError("parser response is missing its parser metadata")
        parser_name = parser_info.get("name")
        parser_version = parser_info.get("version")
        parser_standards = parser_info.get("standards")
        if (
            not isinstance(parser_name, str)
            or not parser_name.strip()
            or parser_name != "SysML v2 Language Server (ANTLR)"
            or not isinstance(parser_version, str)
            or not parser_version.strip()
            or not isinstance(parser_standards, list)
            or any(not isinstance(standard_name, str) for standard_name in parser_standards)
            or not {
                "SysML v2 textual grammar derived from OMG KEBNF",
                "KerML textual grammar derived from OMG KEBNF",
            }.issubset(parser_standards)
        ):
            raise ParserBackendError(
                "parser metadata must identify the SysML v2 LSP, its version, and its OMG KEBNF-derived grammars"
            )

        response_files = response.get("files")
        if not isinstance(response_files, list):
            raise ParserBackendError("parser response is missing its files list")

        expected_paths = {source["path"] for source in parser_inputs}
        parsed_files = []
        for file_response in response_files:
            if not isinstance(file_response, dict):
                raise ParserBackendError("parser response contains a non-object file entry")
            parsed_files.append(self._parse_file(file_response, parser_name))

        actual_paths = [parsed.path for parsed in parsed_files]
        if len(actual_paths) != len(set(actual_paths)) or set(actual_paths) != expected_paths:
            raise ParserBackendError("parser response file paths do not match the requested workspace files")
        return parser_info, parsed_files

    @classmethod
    def _parse_file(cls, file_response: dict[str, Any], parser_name: str) -> ParsedFile:
        file_path = cls._required_string(file_response, "path")
        symbols = [
            Symbol(
                name=cls._required_string(symbol, "name"),
                kind=cls._required_string(symbol, "kind"),
                file=file_path,
                range=cls._parse_range(symbol.get("range")),
                container=cls._optional_string(symbol.get("container"), "symbol container"),
                signature=cls._optional_string(symbol.get("signature"), "symbol signature"),
            )
            for symbol in cls._object_list(file_response, "symbols")
        ]
        references = [
            Reference(
                name=cls._required_string(reference, "name"),
                file=file_path,
                range=cls._parse_range(reference.get("range")),
                relation=cls._optional_string(reference.get("relation"), "reference relation"),
                source=cls._optional_string(reference.get("source"), "reference source"),
            )
            for reference in cls._object_list(file_response, "references")
        ]
        diagnostics = []
        for diagnostic in cls._object_list(file_response, "diagnostics"):
            severity = cls._required_string(diagnostic, "severity")
            if severity not in {"error", "warning", "info"}:
                raise ParserBackendError(f"parser returned unsupported diagnostic severity: {severity}")
            diagnostics.append(
                Diagnostic(
                    file=file_path,
                    range=cls._parse_range(diagnostic.get("range")),
                    severity=severity,
                    message=cls._required_string(diagnostic, "message"),
                    source=cls._optional_string(diagnostic.get("source"), "diagnostic source") or parser_name,
                )
            )

        imports = file_response.get("imports")
        if not isinstance(imports, list) or any(not isinstance(import_name, str) for import_name in imports):
            raise ParserBackendError(f"parser returned an invalid imports list for {file_path}")
        return ParsedFile(
            path=file_path,
            symbols=symbols,
            references=references,
            diagnostics=diagnostics,
            imports=imports,
        )

    @staticmethod
    def _required_string(payload: Mapping[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ParserBackendError(f"parser response field {key!r} must be a non-empty string")
        return value

    @staticmethod
    def _optional_string(value: Any, field_name: str) -> str | None:
        if value is not None and not isinstance(value, str):
            raise ParserBackendError(f"parser response field {field_name!r} must be a string or null")
        return value

    @staticmethod
    def _object_list(payload: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
        values = payload.get(key)
        if not isinstance(values, list) or any(not isinstance(value, dict) for value in values):
            raise ParserBackendError(f"parser response field {key!r} must be a list of objects")
        return values

    @staticmethod
    def _parse_range(value: Any) -> Range:
        if not isinstance(value, dict):
            raise ParserBackendError("parser response range must be an object")
        coordinates = [value.get("line"), value.get("col"), value.get("end_col")]
        if any(not isinstance(coordinate, int) or isinstance(coordinate, bool) for coordinate in coordinates):
            raise ParserBackendError("parser response range coordinates must be integers")
        line, col, end_col = coordinates
        if line < 1 or col < 0 or end_col < col:
            raise ParserBackendError("parser response contains an invalid source range")
        return Range(line=line, col=col, end_col=end_col)

    def symbols(self, query: str | None = None) -> list[dict[str, Any]]:
        symbol_records = [
            asdict(symbol)
            for symbols_for_name in self.symbols_by_name.values()
            for symbol in symbols_for_name
        ]
        if query:
            query_lower = query.lower()
            symbol_records = [
                symbol_record
                for symbol_record in symbol_records
                if query_lower in symbol_record["name"].lower()
                or query_lower in symbol_record["kind"].lower()
            ]
        return sorted(
            symbol_records,
            key=lambda symbol_record: (
                symbol_record["name"],
                symbol_record["file"],
                symbol_record["range"]["line"],
            ),
        )

    def definition(self, name: str) -> dict[str, Any] | None:
        matching_symbols = self.symbols_by_name.get(name, [])
        return asdict(matching_symbols[0]) if matching_symbols else None

    def references(self, name: str) -> list[dict[str, Any]]:
        return [
            asdict(reference)
            for reference in self.references_by_name.get(name, [])
        ]

    def hover(self, name: str) -> dict[str, Any] | None:
        symbol_record = self.definition(name)
        if not symbol_record:
            return None
        return {
            "name": symbol_record["name"],
            "kind": symbol_record["kind"],
            "container": symbol_record.get("container"),
            "signature": symbol_record.get("signature"),
            "location": {
                "file": symbol_record["file"],
                "line": symbol_record["range"]["line"],
            },
        }

    def completion(self, prefix: str) -> list[dict[str, str]]:
        prefix_lower = prefix.lower()
        return [
            {"label": symbol_name, "kind": matching_symbols[0].kind}
            for symbol_name, matching_symbols in sorted(self.symbols_by_name.items())
            if symbol_name.lower().startswith(prefix_lower)
        ]

    def diagnostics(self) -> list[dict[str, Any]]:
        return [
            asdict(diagnostic)
            for parsed_file in self.files.values()
            for diagnostic in parsed_file.diagnostics
        ]

    def tree(self) -> dict[str, Any]:
        by_file: dict[str, list[dict[str, Any]]] = {}
        for file_path, parsed in sorted(self.files.items()):
            by_file[file_path] = [
                {
                    "name": symbol.name,
                    "kind": symbol.kind,
                    "line": symbol.range.line,
                    "container": symbol.container,
                }
                for symbol in parsed.symbols
            ]
        return {"root": str(self.root), "files": by_file}

    def query(self, kind: str, name: str | None = None) -> list[dict[str, Any]]:
        symbol_records = [
            asdict(symbol)
            for symbols_for_name in self.symbols_by_name.values()
            for symbol in symbols_for_name
        ]
        kind_query = kind.lower()
        matching_symbols = [
            symbol_record
            for symbol_record in symbol_records
            if kind_query in symbol_record["kind"].lower()
        ]
        if name:
            name_query = name.lower()
            matching_symbols = [
                symbol_record
                for symbol_record in matching_symbols
                if name_query in symbol_record["name"].lower()
            ]
        return sorted(
            matching_symbols,
            key=lambda symbol_record: (symbol_record["name"], symbol_record["file"]),
        )

    def health(self) -> dict[str, Any]:
        graphviz_path = shutil.which("dot")
        parser_status = self.parser_adapter.capabilities()
        parser_status["response_validated"] = bool(self.parser_info)
        return {
            "workspace": str(self.root),
            "files_indexed": len(self.files),
            "symbols": sum(len(symbols_for_name) for symbols_for_name in self.symbols_by_name.values()),
            "graphviz_dot": graphviz_path,
            "parser": {
                **parser_status,
                "active": self.parser_info,
            },
            "capabilities": {
                "language_server_configured": self.parser_adapter.available(),
                "text_views": True,
                "dot_views": True,
                "svg_views": bool(graphviz_path),
            },
        }
