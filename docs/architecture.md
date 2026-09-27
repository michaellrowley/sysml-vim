# Architecture

- Editor front-end (Vimscript): commands, mappings, quickfix, buffers
- Backend service (Python): parser, index, diagnostics, query, views
- CLI (`sysml`) and JSON-RPC (`sysml-rpc`) are editor-independent interfaces
- Rendering layer: text, DOT, SVG
- Official tooling boundary: `OfficialPilotAdapter` invoked by `SYSML_PILOT_COMMAND`

This keeps editor logic thin and backend reusable for CI/automation.
