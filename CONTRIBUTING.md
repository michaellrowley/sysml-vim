# Contributing

## Development workflow

1. Create a branch
2. Install dev deps: `python -m pip install -e .[dev]`
3. Run tests: `pytest -q`
4. Run Vim/Neovim smoke checks
5. Submit PR with test output and capability/conformance impact

The default tests isolate the backend with a static LSP protocol test double. For changes to the parser adapter or model projection, install the pinned language server as described in [the parser setup](docs/lsp-parser.md), then run the real-package integration test:

```sh
SYSML_LSP_SERVER="$HOME/.local/share/sysml-vim/lsp/node_modules/sysml-v2-lsp/dist/server/server.js" \
  pytest -q tests/test_lsp_integration.py
```

## Standards alignment

Do not claim full SysML/KerML conformance unless proven by grammar-derived tests.
Keep official-tooling integration behind explicit adapters and clear capability flags.

## Coding-agent guidance

Read the repository's `AGENTS.md` and the relevant focused guide under
`.github/skills/` before making changes. Keep affected skills current when
verified behavior or an agent mistake reveals a durable change to project
guidance; see [the skill maintenance guide](docs/agent-skills.md).
