# Views

Supported view types:

- package/tree
- composition
- connections
- requirements
- traceability
- dependencies
- behavior
- state

Formats:

- text (terminal-friendly)
- dot (Graphviz)
- svg (if Graphviz `dot` is installed)
- json
- graph (structural diagram with typed definition boxes and feature compartments)
- graph-json (graph text and structured geometry for editor integrations)

Vim command:

- `:v2 graph [focus]` renders a Cameo-inspired structural diagram in a Vim
  buffer. Definitions are shown as boxes with kind/name headers and contained
  usages in feature compartments. Forward relationships use orthogonal routes
  between boxes; backward and cyclic relationships use an outer gutter.
  Unconnected definitions are packed into compact rows below connected
  structures. Box labels wrap to fit the available Vim window width.
  Graph layouts reflow to the narrowest window displaying them after splits or
  resizes. Every graph window disables Vim's line wrapping to preserve box
  alignment; use horizontal scrolling (`zh` / `zl`) for any remaining overflow.
  Relationship labels are listed below the diagram. When `focus` names a
  SysML view usage, the graph renders its exposed elements and their available
  typing/connection relationships, restricted by the associated view
  definition's `viewFilters`, instead of showing the view usage as a standalone
  node. Package wildcard exposures such as `Package::**` expand recursively
  within the resolved package scope. Named interface connection usages are
  rendered as labeled edges when declared with `connect`, including typed
  interface usages.

Within a graph buffer, arrow keys trace outward from the selected box and move
to the first node hit in that direction. If no ray intersects a node, they
move to the nearest node in that half-plane.
Use `]n` / `[n` to move through nodes in layout order and `]e` / `[e` to move
through edges. With mouse support enabled (`mouse=a`), hovering over a node or
rendered edge selects it in Neovim; in Vim, click to select because Vim does
not report pointer-hover events. Selection highlighting is limited to the
selected node's box or the selected edge's entry, rather than extending across
the full screen.

Node boxes are colored by element family. Edge paths use one consistent color,
while edge entries use relationship-family colors; only actual crossing
junctions receive a separate highlight. This keeps a path from appearing to
change color as it overlaps another edge. Highlight groups follow standard Vim
colorscheme groups and can be customized with `:highlight link`: node groups are
`SysmlGraphNodeStructure`, `SysmlGraphNodeInterface`,
`SysmlGraphNodeBehavior`, `SysmlGraphNodeRequirement`, and
`SysmlGraphNodeOther`; routes use `SysmlGraphEdgeRoute`; edge entries use
`SysmlGraphEdgeContainment`,
`SysmlGraphEdgeTyping`, `SysmlGraphEdgeDerivation`,
`SysmlGraphEdgeRequirement`, `SysmlGraphEdgeDependency`, and
`SysmlGraphEdgeOther`. `SysmlGraphJunction` controls shared-route highlighting.
