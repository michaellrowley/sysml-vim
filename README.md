# sysml-vim

A usable SysML v2 / KerML backend + CLI with Vim and Neovim integration.

## Intro

`sysml-vim` gives you a Vim/Neovim-first workflow for SysML v2 and KerML: edit textual models, run checks, and inspect semantic views from the same environment.

The screenshots below were generated from the included example model at `/home/runner/work/sysml-vim/sysml-vim/tests/fixtures/workspace/vehicle.sysml` and backend view output.

### Editing a SysML model in Vim

![Vim editing a SysML model](docs/images/vim-editing.png)

### Block node/edge model graph in Vim (`:SysmlGraph Vehicle`)

![Vim showing block-based ELK-style graph view](docs/images/vim-block-graph.png)

## Status and conformance stance

- Parsing and editor diagnostics are provided by the third-party `sysml-v2-lsp` server, whose ANTLR grammar is generated from OMG SysML/KerML textual KEBNF.
- The Python backend contains no SysML grammar or subset-parser fallback. Commands requiring a model index fail clearly until the language server is installed.
- The language server's semantic checks and model projection are not the official Pilot validator and are not a claim of complete normative SysML 2.0/KerML 1.0 conformance.
- Indexing and views expose selected model elements and relationships; they are editor conveniences, not a claim of complete SysML 2.0/KerML 1.0 semantic conformance.

## Upstream references used

Checked on 2026-09-27:

- `Systems-Modeling/SysML-v2-Release` HEAD: `fb97b754f29588b8e9c7a35f370880cd15eb29e7` (release `2026-08`)
- `daltskin/sysml-v2-grammar` HEAD: `14b0d7a26d369a0096ac8b5db4d90685e1498b47` (ANTLR grammar generated from the `2026-08` KEBNF release)
- `daltskin/sysml-v2-lsp` HEAD: `2cb64aaf43c05f0921f4fa4c640d69b44d189e13` (npm package `0.31.0`)
- The grammar and language server are community-maintained integrations; their tests and diagnostics do not establish official conformance.

## Features

### Backend + CLI (`sysml`)

- Workspace indexing for `.sysml` and `.kerml`
- Symbols, references, definition, hover, completion
- Syntax and language-server diagnostics for `.sysml` and `.kerml` documents
- Semantic queries (`sysml query`)
- Structural tree (`sysml tree`)
- Semantic views: package/composition/connections/requirements/traceability/dependencies/behavior/state
- Rendering formats: text, Graphviz DOT, SVG (when `dot` is installed)
- JSON-RPC server (`sysml-rpc`) with documented methods
- SysML v2 language-server integration via `SYSML_LSP_SERVER` or `SYSML_LSP_COMMAND`

### Vim / Neovim plugin

- Filetype detection for `.sysml` and `.kerml`
- Syntax highlighting, indentation, fold expression with folds open by default, comments
- Commands: `:SysmlCheck`, `:SysmlTree`, `:SysmlView`, `:SysmlFind`, `:SysmlDefinition`, `:SysmlReferences`, `:SysmlHover`, `:SysmlHealth`
- `<Plug>` mappings and non-destructive defaults (`gd`, `gr`, `K`)
- Quickfix integration for diagnostics/references/queries
- Async check path where Vim `job_start()` is available
- Persistent RPC backend mode (`sysml-rpc`) with safe fallback to one-shot CLI invocations
- Block-based node/edge model view in Vim via `:SysmlGraph` with ELK-style hierarchical layered layout
- Tree, graph, and semantic views open in a dedicated full-screen tab and refresh from unsaved model buffers

## Quick start

```bash
python3 -m pip install -e .
npm install --prefix "$HOME/.local/share/sysml-vim/lsp" --no-save --no-package-lock --ignore-scripts sysml-v2-lsp@0.31.0
export SYSML_LSP_SERVER="$HOME/.local/share/sysml-vim/lsp/node_modules/sysml-v2-lsp/dist/server/server.js"
sysml health --path .
sysml parser-status
sysml check tests/fixtures/workspace
sysml view composition --path tests/fixtures/workspace --format text
```

The language server requires Node.js 20 or newer. The `sysml-rpc` backend keeps its LSP process alive and reuses the server's parse cache for an unchanged workspace. See [the complete setup](docs/lsp-parser.md). Without the language server, model commands report an explicit error rather than using an incomplete parser.

### Full one-line Vim install (macOS)

Requires Homebrew. This clones sysml-vim into Vim's package directory and runs the installer, which installs missing prerequisites, the pinned LSP package, a dedicated Python environment, and Vim configuration:

```sh
brew install git && mkdir -p "$HOME/.vim/pack/plugins/start" && git clone https://github.com/michaellrowley/sysml-vim "$HOME/.vim/pack/plugins/start/sysml-vim" && "$HOME/.vim/pack/plugins/start/sysml-vim/tools/install.sh"
```

For an existing checkout, run `./tools/install.sh` from its root. See [the installer details](docs/installation.md) and [manual setup](docs/lsp-parser.md). Vim/Neovim (with native packages, vim-plug, or lazy.nvim) can also load the repository directly.

## JSON-RPC protocol (`sysml-rpc`)

Line-delimited JSON-RPC 2.0 over stdio.

Methods:

- `check`, `symbols`, `definition`, `references`, `hover`, `completion`, `query`, `tree`, `view`, `view_text`, `view_graph`, `health`, `parser_status`, `shutdown`

Example request line:

```json
{"jsonrpc":"2.0","id":1,"method":"definition","params":{"path":".","name":"Vehicle"}}
```

## Documentation

- `docs/installation.md`
- `docs/configuration.md`
- `docs/commands.md`
- `docs/mappings.md`
- `docs/views.md`
- `docs/model-browser.md`
- `docs/api.md`
- `docs/architecture.md`
- `docs/conformance.md`
- `docs/lsp-parser.md`
- `docs/troubleshooting.md`
- `docs/development.md`
- Vim help: `:help sysml-vim`

## Development

```bash
python -m pip install -e .[dev]
pytest -q
```

See `CHANGELOG.md` and `CONTRIBUTING.md`.
