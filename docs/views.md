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
- graph (block-based node/edge view with ELK-style layered hierarchy)

Vim command:

- `:SysmlGraph [focus]` renders a block-based hierarchical composition graph in a Vim buffer.

Within a graph buffer, arrow keys move to the nearest node in that direction.
Use `]n` / `[n` to move through nodes in layout order and `]e` / `[e` to move
through edges. With mouse support enabled (`mouse=a`), hovering over a node or
rendered edge selects it in Neovim; in Vim, click to select because Vim does
not report pointer-hover events. The cursorline highlights the current
selection.
