# Changelog

## Unreleased

- Removed the line-oriented SysML subset parser; workspace parsing and validation now require an explicit bridge to the official SysML v2 Pilot.
- Added a documented JSON contract for official Pilot parser metadata, model projections, and diagnostics, with strict response validation and explicit transport/response errors.
- Removed implicit local fallback from parser-dependent CLI and RPC operations; retained Vim/Neovim indexing, navigation, quickfix, and view workflows when the bridge is configured.
- Added the Java bridge and Python launcher that compile against the official Pilot fat JAR, initialize the Xtext parser/validator, and document end-to-end installation.
- Added a one-command macOS installer for the Pilot, its Java/Python prerequisites, a dedicated backend environment, and Vim configuration.
- Packaged the Pilot bridge as a Python environment command so Vim configuration does not depend on the sysml-vim checkout path.
- Fixed persistent Vim RPC job reuse so consecutive diagnostics and graph requests work with Vim's job objects.

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
