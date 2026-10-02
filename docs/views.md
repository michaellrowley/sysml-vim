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

- text (terminal-friendly; standard view presentations use their view-specific layout)
- dot (Graphviz; uses the selected presentation's nodes and relationships)
- svg (if Graphviz `dot` is installed; geometry views use its `neato` layout engine)
- json
- graph (structural diagram with typed definition boxes and feature compartments)
- graph-json (graph text and structured geometry for editor integrations)

## Standard SysML v2 view definitions

When `focus` names a SysML view usage, sysml-vim resolves its declared view
definition from the LSP projection or typing relationship. It follows projected
specialization and type attributes, so a project-specific view definition can
inherit a standard presentation. The view usage name does not select the style.
A view whose type cannot be resolved to one of the standard definitions below
keeps the existing generic graph presentation.

The standard definitions are listed in the OMG SysML v2 standard library's
[StandardViewDefinitions.sysml](https://github.com/Systems-Modeling/SysML-v2-Release/blob/master/sysml.library/Systems%20Library/StandardViewDefinitions.sysml).
sysml-vim renders their documented intent as follows:

| Standard view definition | Presentation |
| --- | --- |
| `GeneralView` | General node-and-edge graph of exposed model elements and available relationships. |
| `InterconnectionView` | Part usages are nodes; nested part usages and projected features found through their part-type chain are grouped with their owners. Port features are marked with dots on the node border and anchor projected connection edges when their ownership and endpoints are available. Flow usages declared by an interface definition are mapped onto visible usages typed by that definition when exactly two end ports are projected. sysml-vim maps the first and second declared ends to the connection's first and second endpoints to preserve flow direction, and `itemType` labels each route. Direct flow usages connect their projected endpoint parts/features. Connector or interface usages label connection edges. Unowned interface-end features are omitted rather than shown as peer parts. Definition-only nodes are omitted. |
| `ActionFlowView` | Actions and control nodes are promoted to nodes; parts can provide context, parameters are shown with direction when projected, and flow, binding, and succession relationships are edges. |
| `StateTransitionView` | State usages are nodes, nested states remain visible, and projected transitions are routed between states, including self-transitions. Actions owned by states remain state features. |
| `SequenceView` | Exposed participant features form horizontal lifelines; projected event/action usages and messages are placed top-to-bottom by source location. The source order is a presentation order, not simulated execution time. |
| `GeometryView` | Numeric projected positions are shown in XY, and also XZ/YZ orthographic plots when 3D coordinates are available. Unlocated elements remain in the coordinate inventory. If positions are absent, the view reports that and shows an inventory instead of inventing placement. This is not a solid-shape or full 3D geometry renderer. |
| `GridView` | Exposed elements appear in a width-aware table with kind, type, owner, and projected relationships; edges are also listed for navigation. |
| `BrowserView` | Exposed elements appear as a hierarchy. In Vim/Neovim graph buffers, indentation folds make branches expandable and collapsible (`zc` / `zo`, `zM` / `zR`). |

The view's `viewFilters` and exposures still select model elements; the resolved
view definition selects how those elements are presented. Graph and graph-json
layouts include a `presentation` field for editor integrations. Text, DOT, and
SVG rendering use the same resolved presentation. For example:

```vim
:V2g bleTraceView
:v2 view composition bleTraceView
```

```sh
sysml view composition --focus bleTraceView --format graph
sysml view composition --focus bleTraceView --format graph-json
```

Only relationships and attributes present in the language-server projection
are rendered. In particular, sequence order is based on source locations and
geometry is limited to numeric projected positions; neither is inferred from
SysML syntax or claimed to be a complete semantic rendering.

Vim command:

- `:v2 graph [focus]` renders a Cameo-inspired structural diagram in a Vim
  buffer. For the generic graph, definitions are shown as boxes with kind/name
  headers and contained usages in feature compartments. Forward relationships use orthogonal routes
  between boxes; backward and cyclic relationships use an outer gutter.
  Unconnected definitions are packed into compact rows below connected
  structures. Box labels wrap to fit the available Vim window width.
  Graph layouts reflow to the narrowest window displaying them after splits or
  resizes. Every graph window disables Vim's line wrapping to preserve box
  alignment; use horizontal scrolling (`zh` / `zl`) for any remaining overflow.
  Relationship labels are listed below the diagram; interconnection labels are
  also drawn on their routes. The layout expands beyond the requested width
  when necessary to fit annotations, so horizontal scrolling may be needed.
  If a route has no clear horizontal run, its annotation is attached on an
  overflow spur outside the nodes. When `focus` names a
  SysML view usage, the graph renders its exposed elements and their available
  typing/connection relationships, restricted by the associated view
  definition's `viewFilters`, instead of showing the view usage as a standalone
  node. Package wildcard exposures such as `Package::**` expand recursively
  within the resolved package scope. Named interface connection usages are
  rendered as labeled edges when declared with `connect`, including typed
  interface usages. For `InterconnectionView`, dots on part-node borders mark
  projected ports and connection routes meet those dots. Projected item-flow
  relationships use projected `flowSource`/`flowTarget` paths and the
  `itemType` as a `◆` route marker when available. For interface-typed flows,
  the graph maps the definition's first and second end ports to a visible
  connection usage's first and second endpoints. This is projection-based
  presentation behavior, not a claim of complete SysML semantics. DOT/SVG
  output uses record fields to anchor edges to projected feature rows.

Within a graph buffer, arrow keys trace outward from the selected box and move
to the first node hit in that direction. If no ray intersects a node, they
move to the nearest node in that half-plane.
Use `]n` / `[n` to move through nodes in layout order and `]e` / `[e` to move
through edges. With mouse support enabled (`mouse=a`), hovering over a node or
rendered edge selects it in Neovim; in Vim, click to select because Vim does
not report pointer-hover events. Selection highlighting is limited to the
selected node's box or the selected edge's route and entry, rather than
extending across the full screen.
Press `<CR>` on a selected node or edge to open its projected details in a
read-only tab. Node details show the projected feature hierarchy and related
relationships. Interconnection-edge details show the interface usage, both
endpoint part/port hierarchies, and projected flows or bindings touching those
hierarchies. These details reflect only the available language-server
projection and do not imply complete SysML/KerML semantics.

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
