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

In `:SysmlGraph` buffers, `]n` / `[n` move to the next / previous node, and
`]e` / `[e` move to the next / previous edge. The graph-only defaults respect
existing mappings and can be replaced using the corresponding `<Plug>` maps.
Arrow keys move to the nearest node in that direction. With mouse support
enabled (`mouse=a`), pointing at a node or rendered edge selects it in Neovim;
in Vim, click to select because it does not report pointer-hover events.
