# Commands

## CLI

- `sysml check [path]`
- `sysml symbols [path] [--query Q]`
- `sysml definition NAME [--path P]`
- `sysml references NAME [--path P]`
- `sysml hover NAME [--path P]`
- `sysml completion PREFIX [--path P]`
- `sysml query KIND [--name N] [--path P]`
- `sysml tree [path]`
- `sysml view TYPE [--focus E] [--depth N] [--path P] [--format text|dot|svg|json|graph|graph-json]`
- `sysml health [--path P]`
- `sysml parser-status`

All commands that read a model require the configured SysML language server. See [installation](installation.md) and [the parser integration guide](lsp-parser.md).

## Vim commands

- `:v2 check [path]`
- `:v2 check-workspace [path]`
- `:v2 tree [path]`
- `:v2 view [type] [focus]`
- `:v2 graph [focus]`
- `:v2 find [kind] [name]`
- `:v2 definition [name]`
- `:v2 references [name]`
- `:v2 hover [name]`
- `:v2 relationships [name]`
- `:v2 requirements [name]`
- `:v2 traceability [name]`
- `:v2 health`
- `:v2 log`
- `:v2 restart`
- `:v2 help`

`:v2 check` checks the current model file by default, using its current buffer text; `:v2 check-workspace` checks the current working directory and includes unsaved text from loaded model buffers in that workspace. `:v2 tree`, `:v2 view`, and `:v2 graph` open in a dedicated tab instead of splitting the current window. `:v2 graph` with no argument renders the whole workspace; pass a model element name to focus it. The source tab stays available, and each view refreshes after edits to loaded SysML/KerML buffers in its workspace. The persistent RPC backend sends those buffers' current text, including unsaved edits, to the parser. If RPC is unavailable while model buffers have unsaved changes, checks and views report that they cannot safely use current text rather than displaying stale disk contents.

The lowercase shortcuts are aliases for the full command set:

| Shortcut | Command |
| --- | --- |
| `:v2c [path]` | `:v2 check [path]` |
| `:v2cw [path]` | `:v2 check-workspace [path]` |
| `:v2d [name]` | `:v2 definition [name]` |
| `:v2f [kind] [name]` | `:v2 find [kind] [name]` |
| `:v2g [focus]` | `:v2 graph [focus]` |
| `:v2hea` | `:v2 health` |
| `:v2h` | `:v2 help` |
| `:v2ho [name]` | `:v2 hover [name]` |
| `:v2l` | `:v2 log` |
| `:v2r [name]` | `:v2 references [name]` |
| `:v2rel [name]` | `:v2 relationships [name]` |
| `:v2req [name]` | `:v2 requirements [name]` |
| `:v2res` | `:v2 restart` |
| `:v2tra [name]` | `:v2 traceability [name]` |
| `:v2t [path]` | `:v2 tree [path]` |
| `:v2v [type] [focus]` | `:v2 view [type] [focus]` |

Vim requires user-defined Ex commands to start with an uppercase letter, so command-line abbreviations make the lowercase forms work. The original `:Sysml*` commands remain available for compatibility.
