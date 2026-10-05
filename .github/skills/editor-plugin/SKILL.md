---
name: editor-plugin
description: Use when changing Vim or Neovim commands, mappings, filetype behavior, buffers, quickfix, graph interaction, or editor/backend communication.
---

# Vim and Neovim integration

## Start here

Read `docs/commands.md`, `docs/mappings.md`, and `docs/configuration.md`.
Inspect the relevant files among `plugin/sysml.vim`, `autoload/sysml.vim`,
`ftplugin/`, `syntax/`, `indent/`, and `lua/`.

## Preserve editor behavior

- Keep public command aliases, legacy `:Sysml*` commands, `<Plug>` mappings,
  and documented defaults compatible unless a change is intentional.
- Resolve `g:sysml_backend_cmd` and `g:sysml_rpc_cmd` as a matched pair from
  `SYSML_VIM_INSTALL_ROOT`; if one is explicitly overridden, derive its
  companion from the same executable directory rather than another `PATH`
  entry.
- Vimscript owns editor interactions; Python owns model parsing, indexing, and
  semantic views. Use the documented CLI/RPC boundary instead of duplicating
  model logic in Vimscript.
- Views and checks must use current loaded SysML/KerML buffer text, including
  unsaved and newly named in-workspace documents. If current text cannot be
  sent to the backend, report that stale disk text cannot be used; never imply
  that an unsaved model was checked.
- Preserve clean fallback behavior between persistent RPC and one-shot CLI,
  and keep diagnostics, quickfix, result buffers, and refresh behavior
  consistent with the documented commands.
- Keep graph-json geometry and presentation metadata aligned with Vim hit
  testing; hierarchy presentations may use indent folds but must preserve
  source navigation and graph refresh behavior. Selecting an edge by route or
  with `]e` / `[e` should highlight both its route and edge-list entry; test
  route-cell geometry as well as selection identity. Programmatic graph
  navigation must reveal the selected position in both axes, including when
  the cursor is already there but the view has since scrolled away. Use
  backend-provided graph inspection metadata for selected nodes and edges;
  Vimscript should present projected details rather than reimplement model
  analysis.
- Consider both Vim and Neovim. Validate command registration and run the
  relevant Vim smoke tests; update Neovim-specific behavior/tests when touched.

## Documentation

When a user-visible command, mapping, setting, refresh rule, or interaction
changes, update the matching command/mapping/configuration/help documentation
and this skill if its guidance changed.
