from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Iterable

NAME_RE = r"[A-Za-z_][A-Za-z0-9_]*"
PACKAGE_RE = re.compile(rf"^\s*package\s+({NAME_RE})")
DEF_RE = re.compile(
    rf"^\s*(part|port|interface|requirement|state|action|item|connection|attribute)\s+def\s+({NAME_RE})"
)
USAGE_RE = re.compile(rf"^\s*(part|port|requirement|item|attribute)\s+({NAME_RE})(?:\s*:\s*({NAME_RE}))?")
IMPORT_RE = re.compile(r"^\s*import\s+([A-Za-z0-9_:.]+)")
REL_RE = re.compile(rf"\b(satisfy|verify|allocate|refine|trace|specializes|redefines)\b\s+({NAME_RE})")
TYPE_REF_RE = re.compile(rf":\s*({NAME_RE})\b")
TRANSITION_RE = re.compile(rf"\b({NAME_RE})\s*->\s*({NAME_RE})")


@dataclass(slots=True)
class Range:
    line: int
    col: int
    end_col: int


@dataclass(slots=True)
class Symbol:
    name: str
    kind: str
    file: str
    range: Range
    container: str | None = None
    signature: str | None = None


@dataclass(slots=True)
class Reference:
    name: str
    file: str
    range: Range
    relation: str | None = None


@dataclass(slots=True)
class Diagnostic:
    file: str
    range: Range
    severity: str
    message: str
    source: str = "sysml-vim"


@dataclass(slots=True)
class ParsedFile:
    path: str
    symbols: list[Symbol] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


def _line_range(line_no: int, line: str, token: str) -> Range:
    col = max(line.find(token), 0)
    return Range(line=line_no, col=col, end_col=col + len(token))


def parse_sysml(path: Path, text: str) -> ParsedFile:
    parsed = ParsedFile(path=str(path))
    brace_balance = 0
    package_stack: list[str] = []

    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip("\n")

        brace_balance += line.count("{") - line.count("}")
        if brace_balance < 0:
            parsed.diagnostics.append(
                Diagnostic(
                    file=str(path),
                    range=Range(i, 0, max(1, len(line))),
                    severity="error",
                    message="Unmatched closing brace",
                )
            )
            brace_balance = 0

        pkg_match = PACKAGE_RE.search(line)
        if pkg_match:
            pkg = pkg_match.group(1)
            package_stack = [pkg]
            parsed.symbols.append(
                Symbol(
                    name=pkg,
                    kind="package",
                    file=str(path),
                    range=_line_range(i, line, pkg),
                    signature=line.strip(),
                )
            )

        import_match = IMPORT_RE.search(line)
        if import_match:
            imp = import_match.group(1)
            parsed.imports.append(imp)
            parsed.references.append(
                Reference(
                    name=imp.split("::")[-1],
                    file=str(path),
                    range=_line_range(i, line, imp),
                    relation="import",
                )
            )

        def_match = DEF_RE.search(line)
        if def_match:
            kind = f"{def_match.group(1)}_def"
            name = def_match.group(2)
            parsed.symbols.append(
                Symbol(
                    name=name,
                    kind=kind,
                    file=str(path),
                    range=_line_range(i, line, name),
                    container="::".join(package_stack) if package_stack else None,
                    signature=line.strip(),
                )
            )

        usage_match = USAGE_RE.search(line)
        if usage_match and " def " not in line:
            kind = f"{usage_match.group(1)}_usage"
            name = usage_match.group(2)
            parsed.symbols.append(
                Symbol(
                    name=name,
                    kind=kind,
                    file=str(path),
                    range=_line_range(i, line, name),
                    container="::".join(package_stack) if package_stack else None,
                    signature=line.strip(),
                )
            )
            if usage_match.group(3):
                target = usage_match.group(3)
                parsed.references.append(
                    Reference(
                        name=target,
                        file=str(path),
                        range=_line_range(i, line, target),
                        relation="typed_by",
                    )
                )

        for rel in REL_RE.finditer(line):
            rel_name = rel.group(2)
            parsed.references.append(
                Reference(
                    name=rel_name,
                    file=str(path),
                    range=_line_range(i, line, rel_name),
                    relation=rel.group(1),
                )
            )

        for type_ref in TYPE_REF_RE.finditer(line):
            name = type_ref.group(1)
            parsed.references.append(
                Reference(
                    name=name,
                    file=str(path),
                    range=_line_range(i, line, name),
                    relation="type",
                )
            )

        for trans in TRANSITION_RE.finditer(line):
            for name in trans.groups():
                parsed.references.append(
                    Reference(
                        name=name,
                        file=str(path),
                        range=_line_range(i, line, name),
                        relation="transition",
                    )
                )

    if brace_balance > 0:
        parsed.diagnostics.append(
            Diagnostic(
                file=str(path),
                range=Range(max(1, len(text.splitlines())), 0, 1),
                severity="error",
                message="Unclosed brace block",
            )
        )

    return parsed


def parse_path(path: Path) -> ParsedFile:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ParsedFile(
            path=str(path),
            diagnostics=[
                Diagnostic(
                    file=str(path),
                    range=Range(1, 0, 1),
                    severity="error",
                    message="File is not UTF-8 encoded",
                )
            ],
        )
    return parse_sysml(path, text)


def iter_model_files(root: Path) -> Iterable[Path]:
    if root.is_file() and root.suffix.lower() in {".sysml", ".kerml"}:
        yield root
        return
    for path in root.rglob("*"):
        if path.suffix.lower() in {".sysml", ".kerml"} and path.is_file():
            yield path
