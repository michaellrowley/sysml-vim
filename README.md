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

- SysML/KerML files are parsed and validated by a configured bridge to the official SysML v2 Pilot Implementation.
- The Python backend contains no SysML grammar, parser, or local validation fallback. Commands requiring a model index fail clearly until the Pilot bridge is configured.
- Indexing and views expose selected model elements and relationships; they are editor conveniences, not a claim of complete SysML 2.0/KerML 1.0 semantic conformance.

## Upstream references used

Checked on 2026-09-27:

- `Systems-Modeling/SysML-v2-Release` HEAD: `fb97b754f29588b8e9c7a35f370880cd15eb29e7` (release `2026-08`)
- `Systems-Modeling/SysML-v2-Pilot-Implementation` HEAD: `5cca16d846016e62bb1e54e0e50e675254a022ef` (version `0.63.0 (20260901)`)
- Official release repository includes textual/graphical BNF (`bnf/*.kebnf`, `bnf/*.kgbnf`) and model libraries

## Features

### Backend + CLI (`sysml`)

- Workspace indexing for `.sysml` and `.kerml`
- Symbols, references, definition, hover, completion
- Diagnostics returned by the configured Pilot parser and validator
- Semantic queries (`sysml query`)
- Structural tree (`sysml tree`)
- Semantic views: package/composition/connections/requirements/traceability/dependencies/behavior/state
- Rendering formats: text, Graphviz DOT, SVG (when `dot` is installed)
- JSON-RPC server (`sysml-rpc`) with documented methods
- Official parser/validator bridge via `SYSML_PILOT_COMMAND` (argv mode) or `SYSML_PILOT_RPC_COMMAND` (JSON-RPC mode)

### Vim / Neovim plugin

- Filetype detection for `.sysml` and `.kerml`
- Syntax highlighting, indentation, fold expression, comments
- Commands: `:SysmlCheck`, `:SysmlTree`, `:SysmlView`, `:SysmlFind`, `:SysmlDefinition`, `:SysmlReferences`, `:SysmlHover`, `:SysmlHealth`
- `<Plug>` mappings and non-destructive defaults (`gd`, `gr`, `K`)
- Quickfix integration for diagnostics/references/queries
- Async check path where Vim `job_start()` is available
- Persistent RPC backend mode (`sysml-rpc`) with safe fallback to one-shot CLI invocations
- Block-based node/edge model view in Vim via `:SysmlGraph` with ELK-style hierarchical layered layout

## Quick start

```bash
python -m pip install -e .
export SYSML_PILOT_HOME="$HOME/SysML-v2-Pilot-Implementation"
export SYSML_PILOT_COMMAND="sysml-pilot-bridge"
sysml health --path .
sysml check tests/fixtures/workspace
sysml view composition --path tests/fixtures/workspace --format text
```

Installing sysml-vim also installs the `sysml-pilot-bridge` command into the same Python environment. Activate that environment (or add its `bin`/`Scripts` directory to `PATH`), then configure the command without a repository-specific path. The bridge compiles against the Pilot's generated `*-all.jar` on first use. See [the complete setup](docs/pilot-parser.md). Without the Pilot build or a configured bridge, model commands report an explicit error rather than using an incomplete parser.

### Full one-line Vim install (macOS)

Requires Homebrew. This clones sysml-vim into Vim's package directory and runs the installer, which installs missing prerequisites, builds the official Pilot, creates a dedicated Python environment, and configures Vim:

```sh
brew install git && mkdir -p "$HOME/.vim/pack/plugins/start" && git clone https://github.com/michaellrowley/sysml-vim "$HOME/.vim/pack/plugins/start/sysml-vim" && "$HOME/.vim/pack/plugins/start/sysml-vim/tools/install.sh"
```

For an existing checkout, run `./tools/install.sh` from its root. The installer reuses an existing Pilot build; a fresh Pilot build can take several minutes. See [the installer details](docs/installation.md) and [manual setup](docs/pilot-parser.md). Vim/Neovim (with native packages, vim-plug, or lazy.nvim) can also load the repository directly.

## JSON-RPC protocol (`sysml-rpc`)

Line-delimited JSON-RPC 2.0 over stdio.

Methods:

- `check`, `symbols`, `definition`, `references`, `hover`, `completion`, `query`, `tree`, `view`, `view_text`, `view_graph`, `health`, `official`, `official_status`, `shutdown`

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
- `docs/pilot-parser.md`
- `docs/troubleshooting.md`
- `docs/development.md`
- Vim help: `:help sysml-vim`

## Development

```bash
python -m pip install -e .[dev]
pytest -q
```

See `CHANGELOG.md` and `CONTRIBUTING.md`.
