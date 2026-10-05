---
name: backend-interfaces
description: Use when changing sysml CLI commands, output and exit behavior, JSON-RPC methods, request parameters, workspace caching, or API compatibility.
---

# CLI and JSON-RPC interfaces

## Start here

Read `docs/commands.md`, `docs/api.md`, and `docs/configuration.md`. Inspect
`src/sysml_vim/cli.py` and/or `src/sysml_vim/rpc.py`; follow backend behavior
into `WorkspaceIndex` rather than implementing model operations twice.

## Compatibility rules

- Keep CLI and JSON-RPC capabilities aligned where appropriate, including
  view types and formats. Document deliberate differences.
- Keep the editor's `sysml` and `sysml-rpc` executables from the same
  sysml-vim installation under `SYSML_VIM_INSTALL_ROOT`; do not resolve
  mismatched commands independently from `PATH`.
- Preserve JSON-RPC 2.0 line-delimited stdio framing and stable error classes:
  unknown method, invalid parameters, and backend failure must not be reported
  as successful results.
- Keep `health` and `parser_status` usable without starting the language server.
  Model-dependent methods require a configured server and must expose failures.
- Preserve workspace-scoped cache invalidation for file changes and document
  overrides, explicit refresh, and clean server shutdown.
- Treat RPC document overrides as in-memory input: validate their paths and
  scope before indexing, and never write their contents to disk.

## Tests and docs

Update CLI or RPC tests for new methods, parameters, output shapes, exit codes,
and errors. Keep `docs/commands.md` and `docs/api.md` aligned with all
user-visible interface changes.
