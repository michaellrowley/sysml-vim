---
name: verification
description: Use when selecting tests, validating cross-layer changes, or updating project docs and repository skills after behavior changes or agent mistakes.
---

# Verification and durable guidance

## Choose targeted checks

- The default Python suite is `pytest -q`; `tests/conftest.py` configures a
  local protocol test double, so ordinary tests do not need a network-installed
  language server.
- Run the narrowest relevant pytest modules first: adapter/client/parser/
  workspace, CLI/RPC, render/diagram, or plugin files.
- Use `tests/test_lsp_integration.py` with the pinned `SYSML_LSP_SERVER` for
  changes whose correctness depends on the published parser package.
- For editor changes, run relevant Vim smoke scripts:
  `tests/vim_smoke.vim`, `tests/vim_backend_config_smoke.vim`,
  `tests/vim_lsp_smoke.vim`, and `tests/vim_view_smoke.vim`; run
  `tests/nvim_backend_config.lua` when Neovim configuration is affected.
  Check Neovim when available and affected.
- Follow the CI workflow for wider validation. Report checks that could not
  run rather than implying they passed.

## Keep the project guidance useful

When source behavior or a validated convention changes, update directly
affected user documentation and the relevant skill in the same change. Check
README, `docs/`, and Vim help where their content is affected; keep CLI, RPC,
and editor surfaces consistent.

For multi-step work, make small, frequent commits after independently
complete, verified units unless the user asks to leave changes uncommitted.
Keep each commit scoped to the task; do not bundle unrelated work or commit an
incomplete or unverified state. Comments should thoroughly explain non-obvious
intent, invariants, edge cases, tradeoffs, and side effects, remain accurate
after code changes, and avoid narrating what the code already makes clear.

When a test, user correction, or review exposes an agent mistake:

1. Verify the root cause against the implementation and tests.
2. Fix the code or tests when needed; do not replace that fix with a skill edit.
3. Add or correct only the durable, actionable instruction that would prevent
   the mistake in the relevant skill, and cross-link it if another area is
   affected.
4. Avoid incident-specific rules, speculative prohibitions, or copying whole
   documentation pages into skills.

Skills are working aids, not a source of truth. Re-check relevant code and
tests before relying on them, and correct stale guidance when discovered.
