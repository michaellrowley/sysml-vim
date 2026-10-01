---
name: model-views
description: Use when changing workspace indexing, symbols or relationships, semantic queries and views, or text/DOT/SVG/structural graph rendering.
---

# Workspace model and views

## Start here

Read `docs/architecture.md` and `docs/views.md`. Inspect the data types in
`src/sysml_vim/model.py`, indexing and validation in `workspace.py`, and the
relevant projection/rendering code in `render.py` or `diagram.py`.

## Data and behavior principles

- `WorkspaceIndex` is the boundary from validated parser responses to queries
  and rendering. Keep paths, locations, imports, diagnostics, and overrides
  normalized and validated there.
- Preserve unsaved document overrides, including new workspace files not yet
  present on disk. A stale on-disk view must not silently replace current
  editor text.
- Model projections and view relationships are selected capabilities from the
  LSP, not proof of complete SysML/KerML semantics. Do not invent missing
  semantics or imply full conformance.
- Keep view types and output formats coherent across `build_view`, renderer
  functions, CLI/RPC surfaces, and documentation. Rendering should consume the
  shared view model rather than independently re-querying or parsing source.
- Structural graph output is also consumed by editor navigation and highlighting.
  Preserve stable node/edge identity and valid geometry when changing its
  structured output; account for terminal display width when laying out text.

## Tests

Add or update focused workspace, parser-projection, render, or diagram tests
using the existing fixtures and protocol test double. Cover behavior shifts at
the output boundary as well as internal helpers. Update `docs/views.md` when a
user-visible view, format, or interaction changes.
