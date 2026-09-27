# Configuration

## Vim globals

- `g:sysml_backend_cmd` (default: `sysml`)
- `g:sysml_default_view` (default: `composition`)
- `g:sysml_use_rpc` (default: `1`) enables persistent `sysml-rpc` usage with CLI fallback
- `g:sysml_rpc_cmd` (default: `sysml-rpc`)
- `g:sysml_rpc_timeout_ms` (default: `120000`; allows the LSP to start and analyze a workspace)
- `g:sysml_view_refresh_delay_ms` (default: `500`; debounce delay before refreshing open views after model edits)

SysML folds are open by default; set `foldlevel` in your SysML ftplugin or after-ftplugin configuration if you prefer collapsed folds.

## Environment variables

- `SYSML_LSP_SERVER`: path to the installed `sysml-v2-lsp` `dist/server/server.js`; defaults to `~/.local/share/sysml-vim/lsp/node_modules/sysml-v2-lsp/dist/server/server.js`
- `SYSML_LSP_COMMAND`: optional shell-quoted command and arguments for another compatible SysML LSP server; takes precedence over `SYSML_LSP_SERVER`
- `SYSML_NODE_COMMAND`: Node.js executable command (default: `node`)
- `XDG_DATA_HOME`: changes the default user data directory used to locate the LSP package

Install Node.js 20+, the LSP package, and the Python backend as described in [installation](installation.md) and [the parser integration guide](lsp-parser.md). Vim/Neovim must inherit the LSP environment when it starts. There is no built-in subset parser or fallback.

## Health report

Run `:SysmlHealth`, `sysml health --path .`, or `sysml parser-status` to check server configuration without starting Node. Run `sysml check <workspace>` to exercise parsing and collect diagnostics from the language server.
