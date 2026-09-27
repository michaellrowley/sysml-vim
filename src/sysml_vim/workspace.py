from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import shutil
from typing import Any

from .model import Diagnostic, ParsedFile, Reference, Symbol, iter_model_files, parse_path


class WorkspaceIndex:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.files: dict[str, ParsedFile] = {}
        self.symbols_by_name: dict[str, list[Symbol]] = {}
        self.references_by_name: dict[str, list[Reference]] = {}

    def refresh(self) -> None:
        self.files.clear()
        self.symbols_by_name.clear()
        self.references_by_name.clear()

        for file_path in iter_model_files(self.root):
            parsed = parse_path(file_path)
            self.files[parsed.path] = parsed
            for symbol in parsed.symbols:
                self.symbols_by_name.setdefault(symbol.name, []).append(symbol)
            for reference in parsed.references:
                self.references_by_name.setdefault(reference.name, []).append(reference)

        unresolved_seen: set[tuple[str, int, int, str]] = set()
        for refs in self.references_by_name.values():
            for ref in refs:
                if ref.name not in self.symbols_by_name:
                    key = (ref.file, ref.range.line, ref.range.col, ref.name)
                    if key not in unresolved_seen:
                        unresolved_seen.add(key)
                        self.files[ref.file].diagnostics.append(
                            Diagnostic(
                                file=ref.file,
                                range=ref.range,
                                severity="warning",
                                message=f"Unresolved reference: {ref.name}",
                            )
                        )

    def symbols(self, query: str | None = None) -> list[dict[str, Any]]:
        items = [asdict(sym) for syms in self.symbols_by_name.values() for sym in syms]
        if query:
            q = query.lower()
            items = [it for it in items if q in it["name"].lower() or q in it["kind"].lower()]
        return sorted(items, key=lambda it: (it["name"], it["file"], it["range"]["line"]))

    def definition(self, name: str) -> dict[str, Any] | None:
        defs = self.symbols_by_name.get(name, [])
        return asdict(defs[0]) if defs else None

    def references(self, name: str) -> list[dict[str, Any]]:
        return [asdict(ref) for ref in self.references_by_name.get(name, [])]

    def hover(self, name: str) -> dict[str, Any] | None:
        sym = self.definition(name)
        if not sym:
            return None
        return {
            "name": sym["name"],
            "kind": sym["kind"],
            "container": sym.get("container"),
            "signature": sym.get("signature"),
            "location": {"file": sym["file"], "line": sym["range"]["line"]},
        }

    def completion(self, prefix: str) -> list[dict[str, str]]:
        return [
            {"label": name, "kind": syms[0].kind}
            for name, syms in sorted(self.symbols_by_name.items())
            if name.lower().startswith(prefix.lower())
        ]

    def diagnostics(self) -> list[dict[str, Any]]:
        return [asdict(d) for parsed in self.files.values() for d in parsed.diagnostics]

    def tree(self) -> dict[str, Any]:
        by_file: dict[str, list[dict[str, Any]]] = {}
        for file_path, parsed in sorted(self.files.items()):
            by_file[file_path] = [
                {"name": sym.name, "kind": sym.kind, "line": sym.range.line, "container": sym.container}
                for sym in parsed.symbols
            ]
        return {"root": str(self.root), "files": by_file}

    def query(self, kind: str, name: str | None = None) -> list[dict[str, Any]]:
        all_syms = [asdict(sym) for syms in self.symbols_by_name.values() for sym in syms]
        out = [item for item in all_syms if kind.lower() in item["kind"].lower()]
        if name:
            out = [item for item in out if name.lower() in item["name"].lower()]
        return sorted(out, key=lambda item: (item["name"], item["file"]))

    def health(self) -> dict[str, Any]:
        dot = shutil.which("dot")
        return {
            "workspace": str(self.root),
            "files_indexed": len(self.files),
            "symbols": sum(len(v) for v in self.symbols_by_name.values()),
            "graphviz_dot": dot,
            "capabilities": {
                "official_pilot_adapter": "optional_via_env",
                "text_views": True,
                "dot_views": True,
                "svg_views": bool(dot),
            },
        }
