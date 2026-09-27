# Changelog

## Unreleased

- Replaced the official Pilot bridge with a persistent stdio integration to the third-party `sysml-v2-lsp` server and its OMG KEBNF-derived ANTLR grammar.
- Adapted LSP syntax/semantic diagnostics, model projections, document symbols, and reference locations to the existing CLI, RPC, Vim, and graph workflows.
- Added explicit parser metadata and response validation; no local subset parser or fallback is provided, and the LSP semantic checks are not represented as Pilot-equivalent conformance.
- Updated the one-command macOS installer to install Node.js prerequisites, the pinned LSP package, a dedicated Python environment, and Vim configuration.
- Fixed persistent Vim RPC job reuse so consecutive diagnostics and graph requests work with Vim's job objects.

## 0.1.0 - 2026-09-27

- Added Python backend/CLI (`sysml`) and JSON-RPC server (`sysml-rpc`)
- Added workspace indexing, symbols/references, diagnostics, hover/completion, query, tree, views
- Added text/DOT/SVG renderers and Graphviz detection
- Added Vim/Neovim plugin support (commands, mappings, syntax, indent, help)
- Added tests, fixtures, CI workflows, and comprehensive documentation
- Added persistent Vim RPC client mode with safe one-shot CLI fallback
- Expanded fixtures/tests for imports, allocation/traceability, behavior transitions, adapter modes, and new RPC methods
