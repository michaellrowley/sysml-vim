# Development

## Setup

```bash
python -m pip install -e .[dev]
```

The regular test suite uses a static parser-protocol test double and does not need Java or a Pilot checkout. For a real parser integration run, follow [the Pilot bridge setup](pilot-parser.md), build the official Pilot, and set `SYSML_PILOT_HOME` (or `SYSML_PILOT_JAR`) before running tests. `tests/test_pilot_bridge.py` then compiles and exercises the included Java bridge against that build.

## Test

```bash
pytest -q
```

## Vim smoke

```bash
vim -Nu NONE -n -es -S tests/vim_smoke.vim
nvim --headless -u NONE -c "source plugin/sysml.vim" -c "qa" || true
```
