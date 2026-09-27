# Development

## Setup

```bash
python3 -m pip install -e '.[dev]'
```

The regular test suite uses a canned LSP protocol server and does not need Node.js or network access. For integration tests against the published parser, install the package as described in [the parser integration guide](lsp-parser.md), then run:

```sh
SYSML_LSP_SERVER="$HOME/.local/share/sysml-vim/lsp/node_modules/sysml-v2-lsp/dist/server/server.js" \
  pytest -q tests/test_lsp_integration.py
```

The integration test covers part and attribute definitions/usages, a requirement/satisfy relationship, an import, and a syntax error. It verifies parser behavior; it does not establish full normative semantic conformance.

## Test

```bash
pytest -q
```

## Vim smoke

```bash
vim -Nu NONE -n -es -S tests/vim_smoke.vim
vim -Nu NONE -n -es -S tests/vim_view_smoke.vim
nvim --headless -u NONE -c "source plugin/sysml.vim" -c "qa" || true
```
