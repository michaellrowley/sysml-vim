# Contributing

## Development workflow

1. Create a branch
2. Install dev deps: `python -m pip install -e .[dev]`
3. Run tests: `pytest -q`
4. Run Vim/Neovim smoke checks
5. Submit PR with test output and capability/conformance impact

The default tests isolate the backend with a static parser-protocol test double. For changes to the bridge or model projection, also follow [the Pilot setup](docs/pilot-parser.md), build the official Pilot, and run `pytest -q` with `SYSML_PILOT_HOME` set so the optional end-to-end Pilot test runs.

## Standards alignment

Do not claim full SysML/KerML conformance unless proven by grammar-derived tests.
Keep official-tooling integration behind explicit adapters and clear capability flags.
