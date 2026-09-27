# Development

## Setup

```bash
python -m pip install -e .[dev]
```

## Test

```bash
pytest -q
```

## Vim smoke

```bash
vim -Nu NONE -n -es -S tests/vim_smoke.vim
nvim --headless -u NONE -c "source plugin/sysml.vim" -c "qa" || true
```
