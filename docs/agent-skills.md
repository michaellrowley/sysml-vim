# Repository skills for coding agents

This repository keeps focused working guides for Copilot and other coding
agents in `.github/skills/`. The root `AGENTS.md` tells agents to read the
relevant skill before changing code; `.github/copilot-instructions.md` makes the
same entry point explicit for Copilot.

## Skill map

| Skill | Use for |
| --- | --- |
| `architecture` | Module boundaries, project principles, parser and conformance stance |
| `language-server` | LSP transport, parser setup/version, projection, diagnostics, lifecycle |
| `model-views` | Workspace index, model data, semantic views, diagrams and renderers |
| `editor-plugin` | Vim/Neovim commands, mappings, buffers, UI and backend communication |
| `backend-interfaces` | CLI, JSON-RPC, caching, outputs, errors and compatibility |
| `verification` | Test selection, documentation synchronization and durable agent guidance |

For a cross-cutting change, read each skill that directly covers the changed
behavior. Skills supplement, but do not replace, the implementation, tests, or
canonical user documentation. If they disagree, verify the behavior and update
stale skill guidance.

## Maintenance

Update an affected skill in the same change when a verified implementation
change alters its boundaries, invariants, workflow, or test strategy. When an
agent mistake or user correction reveals a durable missing or wrong instruction,
first fix the root cause and then amend the relevant skill so future agents
avoid repeating it. Keep guidance short, actionable, and grounded in tests and
current behavior; link to `docs/` instead of duplicating reference material.

The skills are part of the repository's agent-facing interface. Review them
alongside the code and user docs when making broad architectural or workflow
changes.
