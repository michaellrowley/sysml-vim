---
name: architecture
description: Use when changing sysml-vim architecture, parser boundaries, project principles, supported capabilities, or SysML/KerML conformance claims.
---

# Architecture and project principles

## Start here

Read `docs/architecture.md`, `docs/lsp-parser.md`, and the relevant code before
changing boundaries or describing capabilities. The README and conformance
documentation explain the project's public stance.

## Non-negotiable boundaries

- sysml-vim is a Python backend and CLI with Vim/Neovim integration. It does not
  implement a SysML or KerML grammar.
- Parsing and diagnostics come from the configured third-party `sysml-v2-lsp`
  server. Do not add a local parser, partial grammar, or fallback that appears
  to accept models when the server is absent or fails.
- The language-server adapter maps a selected projection into sysml-vim's
  stable index; the index is not a complete SysML/KerML semantic model.
- Neither third-party parser diagnostics nor a passing parse establish official
  Pilot validation or complete normative SysML 2.0/KerML 1.0 conformance.
- Editor/UI, Python model operations, and rendering have distinct owners. Keep
  their boundaries explicit and avoid placing model semantics in Vimscript.

## Change workflow

1. Identify the owner of the behavior and inspect its callers, tests, and docs.
2. Keep dependencies flowing through the adapter and stable index rather than
   bypassing those boundaries.
3. State capability and conformance limitations accurately in output and docs.
4. Update this skill if a verified architectural invariant or module boundary
   changes; update the relevant focused skill too.
