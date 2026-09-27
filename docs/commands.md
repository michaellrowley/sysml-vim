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
- `sysml view TYPE [--focus E] [--depth N] [--path P] [--format text|dot|svg|json|graph]`
- `sysml health [--path P]`
- `sysml parser-status`

All commands that read a model require the configured SysML language server. See [installation](installation.md) and [the parser integration guide](lsp-parser.md).

## Vim commands

- `:SysmlCheck`
- `:SysmlCheckWorkspace`
- `:SysmlView`
- `:SysmlGraph`
- `:SysmlTree`
- `:SysmlFind`
- `:SysmlDefinition`
- `:SysmlReferences`
- `:SysmlHover`
- `:SysmlHealth`
- `:SysmlLog`
- `:SysmlRestart`

`:SysmlTree`, `:SysmlView`, and `:SysmlGraph` open in a dedicated tab instead of splitting the current window. `:SysmlGraph` with no argument renders the whole workspace; pass a model element name to focus it. The source tab stays available, and each view refreshes after edits to loaded SysML/KerML buffers in its workspace. The persistent RPC backend sends those buffers' current text, including unsaved edits, to the parser. If RPC is unavailable while a model buffer has unsaved changes, the plugin reports that it cannot safely render a current view rather than displaying stale disk contents.
