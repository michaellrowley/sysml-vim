# Installation

## Backend CLI

Install the Python package and development dependencies from a checkout:

```bash
python3 -m pip install -e '.[dev]'
```

Model commands also require Node.js 20 or newer and the SysML v2 language server. The server package is installed separately from Python:

```bash
npm install \
  --prefix "$HOME/.local/share/sysml-vim/lsp" \
  --no-save \
  --no-package-lock \
  --ignore-scripts \
  sysml-v2-lsp@0.31.0
export SYSML_LSP_SERVER="$HOME/.local/share/sysml-vim/lsp/node_modules/sysml-v2-lsp/dist/server/server.js"
```

Run `sysml parser-status` to check configuration and `sysml check <workspace>` to start the server and verify that it can parse model files. Full details and limitations are in [the parser integration guide](lsp-parser.md).

## Automated full install on macOS

With Homebrew installed, this one-line command clones sysml-vim into Vim's package directory and runs its installer:

```sh
brew install git && mkdir -p "$HOME/.vim/pack/plugins/start" && git clone https://github.com/michaellrowley/sysml-vim "$HOME/.vim/pack/plugins/start/sysml-vim" && "$HOME/.vim/pack/plugins/start/sysml-vim/tools/install.sh"
```

The installer uses Homebrew for missing Python 3.11+, Node.js 20+, npm, or Vim dependencies; installs the pinned `sysml-v2-lsp` package; creates a dedicated Python virtual environment; activates the plugin without replacing an existing checkout; and adds an idempotent configuration include to `~/.vimrc`. Restart Vim after it completes. For an existing checkout, run `./tools/install.sh` from its root.

## Vim (vim-plug)

```vim
Plug 'michaellrowley/sysml-vim'
```

Install the Python package and language server as described above, then ensure `SYSML_LSP_SERVER` is set in the environment that starts Vim. The variable can also be assigned in Vim configuration:

```vim
let $SYSML_LSP_SERVER = expand('~/.local/share/sysml-vim/lsp/node_modules/sysml-v2-lsp/dist/server/server.js')
```

## Neovim (lazy.nvim)

```lua
{
  "michaellrowley/sysml-vim",
  config = function()
    vim.g.sysml_backend_cmd = "sysml"
    vim.g.sysml_rpc_cmd = "sysml-rpc"
  end,
}
```

Install the same Python and Node dependencies as for Vim. Neovim must inherit `SYSML_LSP_SERVER`; when using the automated installer, the generated Vim configuration includes it.

## Vim native packages

Clone into `~/.vim/pack/vendor/start/sysml-vim` (or the Neovim equivalent), then run `./tools/install.sh` from that checkout.

## Optional Graphviz for SVG

Install Graphviz and verify:

```bash
dot -V
```
