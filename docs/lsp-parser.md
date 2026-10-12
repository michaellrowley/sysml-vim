# SysML v2 language-server integration

sysml-vim delegates textual parsing, diagnostics, document symbols, references, and model projections to [`daltskin/sysml-v2-lsp`](https://github.com/daltskin/sysml-v2-lsp/tree/main), tracking its moving `main` branch. Its TypeScript server uses generated ANTLR parser code based on the community [`daltskin/sysml-v2-grammar`](https://github.com/daltskin/sysml-v2-grammar), which translates OMG SysML and KerML textual KEBNF. The server projects item-flow payload types and endpoint paths; because anonymous flows may have no projected name, sysml-vim labels them from those endpoints. sysml-vim contains no SysML grammar or local subset-parser fallback.

This is a third-party parser integration, not the OMG Pilot or an official OMG SDK. The LSP project also implements its own semantic checks and a selected model projection. Those checks are not equivalent to the Pilot validator, and neither the parser bridge nor the sysml-vim index claims complete normative SysML 2.0/KerML 1.0 conformance.

## Requirements and installation

- Python 3.11 or newer for the sysml-vim backend.
- Node.js 20 or newer, npm, and Git for installing and building the language server from its GitHub source.
- The `daltskin/sysml-v2-lsp` `main` branch (tested at HEAD `c37e37ce4f07825528f598b18fc694654e7e9223`, package version `0.34.0`).

Install the package into a user data directory:

```sh
data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
install_root=${SYSML_VIM_INSTALL_ROOT:-"$data_home/sysml-vim"}
npm install \
  --prefix "$install_root/lsp" \
  --no-save \
  --no-package-lock \
  --no-audit \
  --no-fund \
  'git+https://github.com/daltskin/sysml-v2-lsp.git#main'
export SYSML_LSP_SERVER="$install_root/lsp/node_modules/sysml-v2-lsp/dist/server/server.js"
```

The Git dependency's `prepare` script compiles the server entry point from
source. The default follows upstream `main`; for a reproducible snapshot,
override `SYSML_LSP_PACKAGE_SPEC` with the same Git URL and a full commit SHA.
The automated installer uses this moving branch by default and configures both
backend executables and the language-server path under the same install root.

The Python backend discovers the server under `SYSML_VIM_INSTALL_ROOT` when
set, otherwise under `XDG_DATA_HOME/sysml-vim` or
`~/.local/share/sysml-vim`:

```text
$SYSML_VIM_INSTALL_ROOT/lsp/node_modules/sysml-v2-lsp/dist/server/server.js
```

Override it when the package is installed elsewhere:

```sh
export SYSML_LSP_SERVER="$HOME/.local/share/sysml-vim/lsp/node_modules/sysml-v2-lsp/dist/server/server.js"
```

When using the default root, the path above is
`~/.local/share/sysml-vim/lsp/node_modules/sysml-v2-lsp/dist/server/server.js`.
When overriding the discovered location, the variable must be present in
Vim/Neovim's launch environment. For GUI editors, set it in their launch
configuration or Vim initialization file. The automated macOS installer sets
it in `~/.vim/sysml-vim.vim`.

Install the Python CLI and RPC service into the same dedicated
`$SYSML_VIM_INSTALL_ROOT/venv` (by default,
`$XDG_DATA_HOME/sysml-vim/venv` or `~/.local/share/sysml-vim/venv`). The editor
uses these paths by default. An unrelated package may provide commands with
the same names but a different parser contract.

To use a compatible server command rather than the packaged Node entry point, set `SYSML_LSP_COMMAND` to a shell-quoted executable and arguments. This is useful for testing and custom packaging. `SYSML_LSP_SERVER` is ignored when a command override is set.

## Verify the setup

```sh
data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
install_root=${SYSML_VIM_INSTALL_ROOT:-"$data_home/sysml-vim"}
sysml="$install_root/venv/bin/sysml"
"$sysml" parser-status
"$sysml" check tests/fixtures/workspace
"$sysml" view composition --path tests/fixtures/workspace --format graph
```

`parser-status` and `health` report configuration without starting Node. The
first model-dependent command starts one LSP process for that workspace. The
persistent `sysml-rpc` service keeps it alive and reuses its parse cache;
one-shot CLI commands start a server for the duration of that command.

## How the adapter uses the server

The Python adapter communicates over the standard LSP `Content-Length`-framed stdio transport. It opens workspace documents, requests the LSP project's `sysml/model` projection and document symbols, collects published syntax/semantic diagnostics, and queries `textDocument/references` for relationship locations. sysml-vim maps those responses into its existing symbol, reference, and diagnostic index; Python continues to render the views and Vim continues to own the editor UI.

The adapter checks the package version, requested files, document versions, source ranges, diagnostic fields, and response shape before indexing. A missing server, malformed response, process failure, or missing per-document diagnostics is an explicit backend error.

## Scope and limitations

- The ANTLR grammar is a community translation of OMG KEBNF; the default Git ref tracks upstream `main` as requested. Use a full commit SHA through `SYSML_LSP_PACKAGE_SPEC` for reproducible installs, and test parser changes against the actual built package.
- Syntax parsing does not by itself provide semantic conformance. The LSP semantic checks are independently implemented and may be incomplete or produce diagnostics that differ from the Pilot.
- The `sysml/model` custom request returns a selected projection, not a complete SysML/KerML semantic model. Some relationships and source locations may not be exposed by that projection.
- The grammar can lag an OMG release or have known translation/error-recovery gaps. A passing parse is not proof that a model satisfies every normative rule.
- The language-server package and grammar repository are MIT-licensed, but the upstream OMG KEBNF has separate provenance and terms. Check upstream notices before redistributing generated grammar files.
- Users who require Pilot-backed validation should run the Pilot separately until a tested conformance comparison demonstrates equivalent coverage.
