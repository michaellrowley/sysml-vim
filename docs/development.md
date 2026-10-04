# Development

## Setup

```bash
data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
export SYSML_VIM_INSTALL_ROOT=${SYSML_VIM_INSTALL_ROOT:-"$data_home/sysml-vim"}
python3 -m venv "$SYSML_VIM_INSTALL_ROOT/venv"
"$SYSML_VIM_INSTALL_ROOT/venv/bin/python" -m pip install -e '.[dev]'
```

The regular test suite uses a canned LSP protocol server and does not need
Node.js or network access. Run it with the same environment's Python:

```bash
"$SYSML_VIM_INSTALL_ROOT/venv/bin/python" -m pytest -q
```

For integration tests against the published parser, install the package as
described in [the parser integration guide](lsp-parser.md), then run:

```sh
SYSML_LSP_SERVER="$SYSML_VIM_INSTALL_ROOT/lsp/node_modules/sysml-v2-lsp/dist/server/server.js" \
  "$SYSML_VIM_INSTALL_ROOT/venv/bin/python" -m pytest -q tests/test_lsp_integration.py
```

The integration test covers part and attribute definitions/usages, a requirement/satisfy relationship, an import, and a syntax error. It verifies parser behavior; it does not establish full normative semantic conformance.

## Test

```bash
"$SYSML_VIM_INSTALL_ROOT/venv/bin/python" -m pytest -q
```

## Vim smoke

```bash
vim -Nu NONE -n -es -S tests/vim_smoke.vim
vim -Nu NONE -n -es -S tests/vim_backend_config_smoke.vim
vim -Nu NONE -n -es -S tests/vim_view_smoke.vim
nvim --headless -u NONE -c "set rtp+=." -c "source plugin/sysml.vim" -c "qa"
nvim --headless -u NONE -c "set rtp+=." -c "luafile tests/nvim_backend_config.lua" -c "qa"
```
