from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


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
    ancestors: tuple[str, ...] = ()
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Reference:
    name: str
    file: str
    range: Range
    relation: str | None = None
    source: str | None = None


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


def iter_model_files(root: Path) -> Iterable[Path]:
    if root.is_file() and root.suffix.lower() in {".sysml", ".kerml"}:
        yield root
        return
    for model_file in sorted(root.rglob("*")):
        if model_file.suffix.lower() in {".sysml", ".kerml"} and model_file.is_file():
            yield model_file
