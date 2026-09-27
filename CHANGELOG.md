# Changelog

## 0.1.0 - 2026-09-27

- Added Python backend/CLI (`sysml`) and JSON-RPC server (`sysml-rpc`)
- Added workspace indexing, symbols/references, diagnostics, hover/completion, query, tree, views
- Added text/DOT/SVG renderers and Graphviz detection
- Added optional official-tooling adapter boundary (`SYSML_PILOT_COMMAND`)
- Added Vim/Neovim plugin support (commands, mappings, syntax, indent, help)
- Added tests, fixtures, CI workflows, and comprehensive documentation
- Added official adapter RPC mode (`SYSML_PILOT_RPC_COMMAND`) and `--official` CLI option with local fallback
- Added persistent Vim RPC client mode with safe one-shot CLI fallback
- Expanded fixtures/tests for imports, allocation/traceability, behavior transitions, adapter modes, and new RPC methods
