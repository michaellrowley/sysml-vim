# Contributing

## Development workflow

1. Create a branch
2. Install dev deps: `python -m pip install -e .[dev]`
3. Run tests: `pytest -q`
4. Run Vim/Neovim smoke checks
5. Submit PR with test output and capability/conformance impact

## Standards alignment

Do not claim full SysML/KerML conformance unless proven by grammar-derived tests.
Keep official-tooling integration behind explicit adapters and clear capability flags.
