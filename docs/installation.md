# Installation

## Backend CLI

```bash
python -m pip install -e .
```

## Vim (vim-plug)

```vim
Plug 'michaellrowley/sysml-vim'
```

## Neovim (lazy.nvim)

```lua
{
  "michaellrowley/sysml-vim",
  config = function()
    vim.g.sysml_backend_cmd = "sysml"
  end,
}
```

## Vim native packages

Clone into `~/.vim/pack/vendor/start/sysml-vim` (or Neovim equivalent).

## Optional Graphviz for SVG

Install `dot` and verify:

```bash
dot -V
```
