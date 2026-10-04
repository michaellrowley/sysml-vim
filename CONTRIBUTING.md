# Contributing

## Development workflow

1. Create a branch
2. Follow the dedicated-environment setup in [the development guide](docs/development.md)
3. Run tests with that environment's Python:
   `"$SYSML_VIM_INSTALL_ROOT/venv/bin/python" -m pytest -q`
4. Run the Vim/Neovim smoke checks from [the development guide](docs/development.md)
5. Submit PR with test output and capability/conformance impact

The default tests isolate the backend with a static LSP protocol test double. For changes to the parser adapter or model projection, install the pinned language server as described in [the parser setup](docs/lsp-parser.md), then run the real-package integration test:

```sh
SYSML_LSP_SERVER="$SYSML_VIM_INSTALL_ROOT/lsp/node_modules/sysml-v2-lsp/dist/server/server.js" \
  "$SYSML_VIM_INSTALL_ROOT/venv/bin/python" -m pytest -q tests/test_lsp_integration.py
```

## Standards alignment

Do not claim full SysML/KerML conformance unless proven by grammar-derived tests.
Keep official-tooling integration behind explicit adapters and clear capability flags.

## Coding-agent guidance

Read the repository's `AGENTS.md` and the relevant focused guide under
`.github/skills/` before making changes. Keep affected skills current when
verified behavior or an agent mistake reveals a durable change to project
guidance; see [the skill maintenance guide](docs/agent-skills.md).
