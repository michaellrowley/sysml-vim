# Instructions for coding agents

Before changing this repository, read the skill or skills relevant to the task.
Skills are focused working guides in `.github/skills/`; use their descriptions
and the map below to select them. Read more than one when a change crosses
boundaries. Do not load unrelated skills just because they exist.

| Work area | Skill |
| --- | --- |
| Repository boundaries, architecture, or SysML/KerML claims | [architecture](.github/skills/architecture/SKILL.md) |
| Parser configuration, LSP protocol, or model projection | [language-server](.github/skills/language-server/SKILL.md) |
| Workspace index, queries, semantic views, or diagrams | [model-views](.github/skills/model-views/SKILL.md) |
| Vim/Neovim commands, buffers, mappings, or UI | [editor-plugin](.github/skills/editor-plugin/SKILL.md) |
| CLI or JSON-RPC behavior and compatibility | [backend-interfaces](.github/skills/backend-interfaces/SKILL.md) |
| Choosing tests, validating changes, or keeping docs aligned | [verification](.github/skills/verification/SKILL.md) |

Skills supplement the source, tests, and user-facing documentation; they do not
replace checking the current implementation. If guidance conflicts with code or
tests, verify the behavior, correct the skill if it is stale, and follow the
verified behavior. Preserve the repository's explicit parser boundary and
conformance limits.

## Commit and comment discipline

- Keep commits small and frequent. For multi-step work, commit each
  independently complete, verified unit promptly rather than collecting all
  finished work into one large final commit, unless the user asks to leave work
  uncommitted. Keep each commit limited to the task's changes; never include
  unrelated pre-existing work or commit an incomplete or unverified change.
- Comment meticulously where explanation matters: record non-obvious intent,
  invariants, edge cases, tradeoffs, and side effects. Keep comments accurate
  and update or remove them when behavior changes. Do not add comments that
  merely narrate obvious code.

Keep the skills accurate as the project evolves. When a change alters an
invariant, workflow, supported interface, test strategy, or other guidance
captured by a skill, update the affected skill in the same change. When a user
or test identifies an agent mistake, fix the underlying issue first, then
update the relevant skill with the durable rule that would have prevented it;
do not add speculative rules or incident-specific workarounds. Keep skill
guidance concise and link to canonical docs instead of copying them.
