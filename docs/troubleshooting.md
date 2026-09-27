# Troubleshooting

- `sysml: command not found`: install backend (`pip install -e .`) and set `g:sysml_backend_cmd`.
- No SVG output: install Graphviz (`dot`) and re-run `sysml health`.
- Empty diagnostics/references: verify file extension is `.sysml` or `.kerml`.
- Need official parser integration: set `SYSML_PILOT_COMMAND` to a compatible adapter command.
