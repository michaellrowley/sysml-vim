---
name: language-server
description: Use when changing SysML language-server configuration, LSP transport, adapter projection, diagnostics, parser versions, or server lifecycle.
---

# Language-server integration

## Start here

Read `docs/lsp-parser.md` and `docs/troubleshooting.md`. Inspect
`src/sysml_vim/adapter.py` and `src/sysml_vim/lsp_client.py`, then locate the
corresponding adapter, client, workspace, and integration tests.

## Integration contract

- `SYSML_LSP_COMMAND` takes precedence over `SYSML_LSP_SERVER`; otherwise the
  adapter discovers the pinned package entry point. Keep configuration and
  health/status reporting consistent with this behavior.
- The client speaks standard Content-Length-framed LSP over stdio, while
  `sysml/model` is a server-specific projection. Do not treat it as a standard
  LSP method or as a complete semantic model.
- Validate response shapes, file coverage, parser metadata, versions, and
  source ranges before indexing. A missing server, malformed response,
  timeout, process failure, or missing diagnostics must remain an explicit
  error, not an empty/success-shaped result.
- Preserve document synchronization and diagnostics for every requested
  document, including unsaved in-memory text. Keep the client reusable for the
  lifetime of persistent RPC where applicable, and close it cleanly.
- Keep the package version pinned. A parser upgrade needs review of upstream
  changes and tests against the real package; do not silently follow a moving
  version.

## Verification and documentation

Use the protocol test double for fast isolated tests. For adapter contract
changes, also run `tests/test_lsp_integration.py` against the pinned package
when available. Do not describe parser success as official conformance. Keep
`docs/lsp-parser.md`, configuration/installation docs, and the verification
skill aligned with changes to requirements or setup.
