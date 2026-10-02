# Conformance and compatibility

## Targeted standards context

- OMG KerML 1.0, SysML 2.0, Systems Modeling API/Services 1.0 (formally adopted; release docs updated 2026-08)
- Upstream refs used:
  - SysML-v2-Release `fb97b754f29588b8e9c7a35f370880cd15eb29e7`
  - `daltskin/sysml-v2-grammar` `14b0d7a26d369a0096ac8b5db4d90685e1498b47`
  - `michaellrowley/sysml-v2-lsp` branch `feat/flow-usage-projection`, HEAD `deedc813f0d4d897869d24ef770321a2d98cecb7` (npm `0.32.0`, fork of `daltskin/sysml-v2-lsp`)

## Parser integration

- ANTLR syntax parser generated from OMG textual KEBNF by a third-party grammar project
- LSP syntax diagnostics, custom semantic checks, cross-file symbol/reference workflows, and selected model projections
- Semantic query and view projections with text/dot/svg outputs
- Vim/Neovim workflows backed by the parser-dependent CLI/backend
- Tests include canned LSP protocol coverage and an optional integration test against the configured Git-pinned package

## Scope and limitations

- The ANTLR grammar is a community translation of OMG KEBNF with downstream patches; grammar translation and parser tests do not certify complete normative syntax coverage
- Semantic diagnostics are implemented by the LSP project and are not equivalent to the Pilot's validation rules
- Complete Systems Modeling API workflow implementation
- Full official graphical notation conformance
- A complete model semantic API: indexing and views expose selected LSP model projections only
- Any local parsing or validation fallback when the language server is missing or fails
