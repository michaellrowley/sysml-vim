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
- For a focused SysML view usage, resolve the typed view definition and its
  projected specialization chain before choosing a standard presentation.
  The LSP may expose view-definition inheritance through type attributes such
  as `partType`, not only `specializes` references. Keep exposure/filter
  selection separate from rendering style, and label any presentation behavior
  that depends on partial LSP attributes or relationships.
- For interconnection diagrams, keep projected features with their part owner.
  Follow projected part-usage/type-definition chains for declared features and
  attach those features to the exposed part usage. Mark projected ports on the
  node border and route supported connection edges to those markers; annotate
  projected item-flow relationships with their item when available. Do not
  promote unowned interface-end or definition features to peer parts; omit them
  when the projection does not connect them to a part, while retaining
  connector relationships that are projected between parts.
- Structural graph output is also consumed by editor navigation and highlighting.
  Preserve stable node/edge identity and valid geometry when changing its
  structured output; account for terminal display width when laying out text.
  Route annotations must remain inside their edge geometry; grow the layout
  beyond a requested viewport width instead of omitting or truncating labels.
  Route hit cells must support highlighting the selected edge path as well as
  its entry. Graph inspection details should derive from the selected projected
  nodes and relationships, preserve nested feature ownership, and remain clear
  that they describe only the available projection.

## Tests

Add or update focused workspace, parser-projection, render, or diagram tests
using the existing fixtures and protocol test double. Cover behavior shifts at
the output boundary as well as internal helpers. Update `docs/views.md` when a
user-visible view, format, or interaction changes.
