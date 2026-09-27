# sysml-vim

A usable SysML v2 / KerML backend + CLI with Vim and Neovim integration.

## Intro

`sysml-vim` gives you a Vim/Neovim-first workflow for SysML v2 and KerML: edit textual models, run checks, and inspect semantic views from the same environment.

The screenshots below were generated from the included example model at `/home/runner/work/sysml-vim/sysml-vim/tests/fixtures/workspace/vehicle.sysml` and backend view output.

### Editing a SysML model in Vim

![Vim editing a SysML model](docs/images/vim-editing.png)

### Semantic composition view output in Vim

![Vim showing semantic composition view output](docs/images/vim-view.png)

## Status and conformance stance

- This release is **usable and tested** for offline structural authoring/navigation workflows.
- It does **not** claim full SysML 2.0/KerML 1.0 semantic conformance.
- It includes an explicit adapter boundary (`SYSML_PILOT_COMMAND`) for invoking official tooling when available.

## Upstream references used

Checked on 2026-09-27:

- `Systems-Modeling/SysML-v2-Release` HEAD: `fb97b754f29588b8e9c7a35f370880cd15eb29e7` (release `2026-08`)
- `Systems-Modeling/SysML-v2-Pilot-Implementation` HEAD: `5cca16d846016e62bb1e54e0e50e675254a022ef` (version `0.63.0 (20260901)`)
- Official release repository includes textual/graphical BNF (`bnf/*.kebnf`, `bnf/*.kgbnf`) and model libraries

## Features

### Backend + CLI (`sysml`)

- Workspace indexing for `.sysml` and `.kerml`
- Symbols, references, definition, hover, completion
- Parse + unresolved-reference diagnostics
- Semantic queries (`sysml query`)
- Structural tree (`sysml tree`)
- Semantic views: package/composition/connections/requirements/traceability/dependencies/behavior/state
- Rendering formats: text, Graphviz DOT, SVG (when `dot` is installed)
- JSON-RPC server (`sysml-rpc`) with documented methods
- Optional official-tooling adapter boundary via `SYSML_PILOT_COMMAND` (argv mode) or `SYSML_PILOT_RPC_COMMAND` (JSON-RPC mode)
- Optional `--official` CLI path for operations (`check`, `definition`, `view`, etc.) with automatic local fallback

### Vim / Neovim plugin

- Filetype detection for `.sysml` and `.kerml`
- Syntax highlighting, indentation, fold expression, comments
- Commands: `:SysmlCheck`, `:SysmlTree`, `:SysmlView`, `:SysmlFind`, `:SysmlDefinition`, `:SysmlReferences`, `:SysmlHover`, `:SysmlHealth`
- `<Plug>` mappings and non-destructive defaults (`gd`, `gr`, `K`)
- Quickfix integration for diagnostics/references/queries
- Async check path where Vim `job_start()` is available
- Persistent RPC backend mode (`sysml-rpc`) with safe fallback to one-shot CLI invocations

## Quick start

```bash
python -m pip install -e .
sysml health --path .
sysml check tests/fixtures/workspace
sysml view composition --path tests/fixtures/workspace --format text
```

Vim/Neovim (with native packages, vim-plug, or lazy.nvim) can load this repository directly; see `docs/installation.md`.

## JSON-RPC protocol (`sysml-rpc`)

Line-delimited JSON-RPC 2.0 over stdio.

Methods:

- `check`, `symbols`, `definition`, `references`, `hover`, `completion`, `query`, `tree`, `view`, `health`, `shutdown`
- `check`, `symbols`, `definition`, `references`, `hover`, `completion`, `query`, `tree`, `view`, `view_text`, `health`, `official`, `official_status`, `shutdown`

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
- `docs/troubleshooting.md`
- `docs/development.md`
- Vim help: `:help sysml-vim`

## Development

```bash
python -m pip install -e .[dev]
pytest -q
```

See `CHANGELOG.md` and `CONTRIBUTING.md`.
