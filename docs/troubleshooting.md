# Troubleshooting

- `sysml: command not found`: install the backend in the dedicated environment as described in [installation](installation.md), or set `g:sysml_backend_cmd` and `g:sysml_rpc_cmd` to the matching executables.
- `sysml health` reports an unexpected parser (for example, Pilot) or the
  backend reports `parser_bridge_configured: false`: Vim is resolving a
  different `sysml`/`sysml-rpc` installation. Point both commands at the same
  sysml-vim virtual environment under
  `$SYSML_VIM_INSTALL_ROOT/venv/bin` (or
  `$XDG_DATA_HOME/sysml-vim/venv/bin`) and restart Vim/Neovim. The full
  installer writes these paths automatically.
- No SVG output: install Graphviz (`dot`; the automated macOS installer adds
  it), verify with `dot -V`, then retry the SVG export.
- `SysML v2 parsing is unavailable`: install Node.js 20+, Git, and the configured `daltskin/sysml-v2-lsp` `main` branch, then configure `SYSML_LSP_SERVER` as shown in [the setup guide](lsp-parser.md).
- `language server command was not found`: verify the first executable in `SYSML_LSP_COMMAND` is on `PATH`, or unset the override and check the `SYSML_LSP_SERVER` path.
- `language server did not publish diagnostics`: confirm the configured server supports LSP diagnostics and that the process can finish parsing the workspace. Run `"$HOME/.local/share/sysml-vim/venv/bin/sysml" check path/to/workspace` from a terminal to see the backend error, adjusting the path for a custom install root.
- `language server returned a stale model`: restart the RPC service with `:v2 restart`; this usually means the server returned data for an older document version.
- Missing or incomplete references/graph edges: the upstream `sysml/model` request exposes a selected projection, not every semantic relationship. Check [the documented limits](lsp-parser.md).
- `sysml-v2-lsp` diagnostics differ from Pilot results: the LSP project's semantic checks are independently implemented and are not Pilot-equivalent validation.
