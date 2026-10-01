# Mappings

Plug mappings:

- `<Plug>(sysml-definition)`
- `<Plug>(sysml-references)`
- `<Plug>(sysml-hover)`
- `<Plug>(sysml-next-diagnostic)`
- `<Plug>(sysml-prev-diagnostic)`
- `<Plug>(sysml-graph-next-node)`
- `<Plug>(sysml-graph-prev-node)`
- `<Plug>(sysml-graph-next-edge)`
- `<Plug>(sysml-graph-prev-edge)`
- `<Plug>(sysml-graph-left)`
- `<Plug>(sysml-graph-right)`
- `<Plug>(sysml-graph-up)`
- `<Plug>(sysml-graph-down)`
- `<Plug>(sysml-graph-mouse)`

Defaults (only if unbound): `gd`, `gr`, `K`.

In `:v2 graph` buffers, `]n` / `[n` move to the next / previous node, and
`]e` / `[e` move to the next / previous edge. The graph-only defaults respect
existing mappings and can be replaced using the corresponding `<Plug>` maps.
BrowserView graph buffers use Vim's indent folds for hierarchy branches; use
`zc` / `zo` to close/open a branch and `zM` / `zR` to close/open all branches.
Arrow keys trace outward from the selected box and move to the first node hit
in that direction; if no ray intersects a node, they move to the nearest node
in that half-plane. With mouse support enabled (`mouse=a`), pointing at a node
or rendered edge selects it in Neovim; in Vim, click to select because it does
not report pointer-hover events.
