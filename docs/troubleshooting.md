# Troubleshooting

- `sysml: command not found`: install backend (`pip install -e .`) and set `g:sysml_backend_cmd`.
- No SVG output: install Graphviz (`dot`; the automated macOS installer adds
  it), verify with `dot -V`, then retry the SVG export.
- `SysML v2 parsing is unavailable`: install Node.js 20+, Git, and the configured `michaellrowley/sysml-v2-lsp` flow-projection branch, then configure `SYSML_LSP_SERVER` as shown in [the setup guide](lsp-parser.md).
- `language server command was not found`: verify the first executable in `SYSML_LSP_COMMAND` is on `PATH`, or unset the override and check the `SYSML_LSP_SERVER` path.
- `language server did not publish diagnostics`: confirm the configured server supports LSP diagnostics and that the process can finish parsing the workspace. Run `sysml check <workspace>` from a terminal to see the backend error.
- `language server returned a stale model`: restart the RPC service with `:v2 restart`; this usually means the server returned data for an older document version.
- Missing or incomplete references/graph edges: the upstream `sysml/model` request exposes a selected projection, not every semantic relationship. Check [the documented limits](lsp-parser.md).
- `sysml-v2-lsp` diagnostics differ from Pilot results: the LSP project's semantic checks are independently implemented and are not Pilot-equivalent validation.
