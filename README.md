# sysml-vim

A usable SysML v2 / KerML backend + CLI with Vim and Neovim integration.

## Intro

`sysml-vim` gives you a Vim/Neovim-first workflow for SysML v2 and KerML: edit textual models, run checks, and inspect semantic views from the same environment.

The screenshots below were generated from the included example model at `/home/runner/work/sysml-vim/sysml-vim/tests/fixtures/workspace/vehicle.sysml` and backend view output.

### Editing a SysML model in Vim

<p float="left">
  <img src="docs/images/vim-editing.png" width="40%" />
  <img src="docs/images/vim-block-graph.png" width="40%" /> 
</p>

### Structural diagram in Vim (`:v2 graph Vehicle`)

Definitions appear as boxes with contained usages in feature compartments.
Orthogonal relationship routes connect boxes, and cyclic relationships use an
outer gutter to keep the structure readable. Unconnected definitions are
packed into compact rows below connected structures.

## Status and conformance stance

- Parsing and editor diagnostics are provided by the third-party `sysml-v2-lsp` server, whose ANTLR grammar is generated from OMG SysML/KerML textual KEBNF.
- The Python backend contains no SysML grammar or subset-parser fallback. Commands requiring a model index fail clearly until the language server is installed.
- The language server's semantic checks and model projection are not the official Pilot validator and are not a claim of complete normative SysML 2.0/KerML 1.0 conformance.
- Indexing and views expose selected model elements and relationships; they are editor conveniences, not a claim of complete SysML 2.0/KerML 1.0 semantic conformance.

## Upstream references used

Checked on 2026-10-02:

- `Systems-Modeling/SysML-v2-Release` HEAD: `fb97b754f29588b8e9c7a35f370880cd15eb29e7` (release `2026-08`)
- `daltskin/sysml-v2-grammar` HEAD: `14b0d7a26d369a0096ac8b5db4d90685e1498b47` (ANTLR grammar generated from the `2026-08` KEBNF release)
- `michaellrowley/sysml-v2-lsp` branch `feat/flow-usage-projection`, HEAD `deedc813f0d4d897869d24ef770321a2d98cecb7` (npm package `0.32.0`, fork of `daltskin/sysml-v2-lsp`)
- The grammar and language server are community-maintained integrations; their tests and diagnostics do not establish official conformance.

## Features

### Backend + CLI (`sysml`)

- Workspace indexing for `.sysml` and `.kerml`
- Symbols, references, definition, hover, completion
- Syntax and language-server diagnostics for `.sysml` and `.kerml` documents
- Semantic queries (`sysml query`)
- Structural tree (`sysml tree`)
- Semantic views: package/composition/connections/requirements/traceability/dependencies/behavior/state
- Focused SysML view usages resolve the standard `GeneralView`,
  `InterconnectionView`, `ActionFlowView`, `StateTransitionView`,
  `SequenceView`, `GeometryView`, `GridView`, or `BrowserView` presentation
- Rendering formats: text, Graphviz DOT, SVG (Graphviz is installed by the
  automated macOS installer), and a structural graph view
- JSON-RPC server (`sysml-rpc`) with documented methods
- SysML v2 language-server integration via `SYSML_LSP_SERVER` or `SYSML_LSP_COMMAND`

### Vim / Neovim plugin

- Filetype detection for `.sysml` and `.kerml`
- Syntax highlighting, indentation, fold expression with folds open by default, comments
- Commands: `:v2 check`, `:v2 tree`, `:v2 view`, `:v2 find`, `:v2 definition`, `:v2 references`, `:v2 hover`, `:v2 health`
- Shortcuts are provided for the full command set; see [the command reference](docs/commands.md). For example, `:v2g` is `:v2 graph`, `:v2h` is `:v2 help`, and `:v2c` is `:v2 check`.
- `<Plug>` mappings and non-destructive defaults (`gd`, `gr`, `K`)
- Quickfix integration for diagnostics/references/queries
- Async check path where Vim `job_start()` is available
- Persistent RPC backend mode (`sysml-rpc`) with safe fallback to one-shot CLI invocations
- Cameo-inspired structural diagram in Vim via `:v2 graph`, with feature
  compartments and orthogonal relationship routing
- Spatial arrow-key node navigation; mouse hover selects nodes and edges in Neovim, with click selection in Vim
- Tree, graph, and semantic views open in a dedicated full-screen tab and refresh from unsaved model buffers

## Quick start

```bash
data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
install_root=${SYSML_VIM_INSTALL_ROOT:-"$data_home/sysml-vim"}
python3 -m venv "$install_root/venv"
"$install_root/venv/bin/python" -m pip install -e .
npm install --prefix "$install_root/lsp" --no-save --no-package-lock --no-audit --no-fund 'git+https://github.com/michaellrowley/sysml-v2-lsp.git#feat/flow-usage-projection'
export SYSML_LSP_SERVER="$install_root/lsp/node_modules/sysml-v2-lsp/dist/server/server.js"
"$install_root/venv/bin/sysml" health --path .
"$install_root/venv/bin/sysml" parser-status
"$install_root/venv/bin/sysml" check tests/fixtures/workspace
"$install_root/venv/bin/sysml" view composition --path tests/fixtures/workspace --format text
```

Keep `sysml` and `sysml-rpc` from this same virtual environment: other packages may install unrelated commands with those names. Vim/Neovim default to the paired executables under this install root, and the full installer also writes both paths explicitly. The language server requires Node.js 20 or newer and Git; npm builds the fork's server from source during installation. The installer tracks the flow-projection branch by default; set `SYSML_LSP_PACKAGE_SPEC` to a full commit ref for a reproducible snapshot. The `sysml-rpc` backend keeps its LSP process alive and reuses the server's parse cache for an unchanged workspace. SVG rendering requires Graphviz (`dot`); the automated macOS installer installs it when missing. See [the complete setup](docs/lsp-parser.md). Without the language server, model commands report an explicit error rather than using an incomplete parser.

### Full one-line Vim install (macOS)

Requires Homebrew. This clones sysml-vim into Vim's package directory and runs the installer, which installs missing prerequisites (including Graphviz for SVG output), the pinned LSP package, a dedicated Python environment, and Vim configuration:

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
- `docs/agent-skills.md`
- Vim help: `:help sysml-vim`

## Development

```bash
data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
install_root=${SYSML_VIM_INSTALL_ROOT:-"$data_home/sysml-vim"}
python3 -m venv "$install_root/venv"
"$install_root/venv/bin/python" -m pip install -e '.[dev]'
"$install_root/venv/bin/python" -m pytest -q
```

See `CHANGELOG.md` and `CONTRIBUTING.md`.
