# Configuration

## Vim globals

- `g:sysml_backend_cmd` (default: `$SYSML_VIM_INSTALL_ROOT/venv/bin/sysml`; the install root defaults to `$XDG_DATA_HOME/sysml-vim` or `~/.local/share/sysml-vim`)
- `g:sysml_default_view` (default: `composition`)
- `g:sysml_use_rpc` (default: `1`) enables persistent `sysml-rpc` usage with CLI fallback
- `g:sysml_rpc_cmd` (default: `$SYSML_VIM_INSTALL_ROOT/venv/bin/sysml-rpc`)
- `g:sysml_rpc_timeout_ms` (default: `120000`; allows the LSP to start and analyze a workspace)
- `g:sysml_view_refresh_delay_ms` (default: `500`; debounce delay before refreshing open views after model edits)

Keep the CLI and RPC commands from the same sysml-vim installation. The default
virtual-environment location is
`$XDG_DATA_HOME/sysml-vim/venv` (or `~/.local/share/sysml-vim/venv` when
`XDG_DATA_HOME` is unset); `SYSML_VIM_INSTALL_ROOT` overrides that root.
When configuring a custom installation manually, set both globals together:

```vim
let g:sysml_backend_cmd = expand('~/.local/share/sysml-vim/venv/bin/sysml')
let g:sysml_rpc_cmd = expand('~/.local/share/sysml-vim/venv/bin/sysml-rpc')
```

Do not rely on generic `sysml`/`sysml-rpc` commands from `PATH` if another
package or checkout also installs those command names.

SysML folds are open by default; set `foldlevel` in your SysML ftplugin or after-ftplugin configuration if you prefer collapsed folds.

## Environment variables

- `SYSML_LSP_SERVER`: path to the installed `sysml-v2-lsp` `dist/server/server.js`; defaults under `$SYSML_VIM_INSTALL_ROOT/lsp` or `~/.local/share/sysml-vim/lsp`
- `SYSML_LSP_COMMAND`: optional shell-quoted command and arguments for another compatible SysML LSP server; takes precedence over `SYSML_LSP_SERVER`
- `SYSML_NODE_COMMAND`: Node.js executable command (default: `node`)
- `SYSML_VIM_INSTALL_ROOT`: installation root used to locate the paired CLI, RPC, and default LSP executables; defaults to `$XDG_DATA_HOME/sysml-vim` or `~/.local/share/sysml-vim`
- `XDG_DATA_HOME`: changes the default user data directory used to locate the sysml-vim installation and LSP package

Install Node.js 20+, the LSP package, and the Python backend as described in [installation](installation.md) and [the parser integration guide](lsp-parser.md). Keep the CLI and RPC executables in this same environment. Vim/Neovim must inherit `SYSML_LSP_COMMAND` or `SYSML_LSP_SERVER` when explicitly configured; the default install root is discovered automatically. There is no built-in subset parser or fallback.

## Health report

Run `:v2 health` in the editor, or use the dedicated CLI executable to check
server configuration without starting Node:

```sh
"$HOME/.local/share/sysml-vim/venv/bin/sysml" health --path .
"$HOME/.local/share/sysml-vim/venv/bin/sysml" parser-status
"$HOME/.local/share/sysml-vim/venv/bin/sysml" check tests/fixtures/workspace
```

Replace the path prefix when using a custom `SYSML_VIM_INSTALL_ROOT` or
`XDG_DATA_HOME`.
