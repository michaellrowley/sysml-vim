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
- `sysml official-status`
- `sysml adapter OP [--path P] [--payload JSON]`

All commands that read a model require a configured official Pilot parser bridge. See [installation](installation.md#sysml-v2-parser-and-validator) and [the bridge contract](pilot-parser.md).

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
