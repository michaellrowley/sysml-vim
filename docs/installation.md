# Installation

## Backend CLI

Install the Python package and development dependencies from a checkout:

```bash
data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
install_root=${SYSML_VIM_INSTALL_ROOT:-"$data_home/sysml-vim"}
python3 -m venv "$install_root/venv"
"$install_root/venv/bin/python" -m pip install -e '.[dev]'
```

Model commands also require Node.js 20 or newer, Git, and the SysML v2 language server. The server package is installed separately from Python and builds from the pinned flow-projection branch:

```bash
data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
install_root=${SYSML_VIM_INSTALL_ROOT:-"$data_home/sysml-vim"}
npm install \
  --prefix "$install_root/lsp" \
  --no-save \
  --no-package-lock \
  --no-audit \
  --no-fund \
  'git+https://github.com/michaellrowley/sysml-v2-lsp.git#feat/flow-usage-projection'
export SYSML_LSP_SERVER="$install_root/lsp/node_modules/sysml-v2-lsp/dist/server/server.js"
```

Run the commands from the dedicated environment to avoid a different `sysml`
package earlier on `PATH`:

```bash
data_home=${XDG_DATA_HOME:-"$HOME/.local/share"}
install_root=${SYSML_VIM_INSTALL_ROOT:-"$data_home/sysml-vim"}
"$install_root/venv/bin/sysml" parser-status
"$install_root/venv/bin/sysml" check tests/fixtures/workspace
```

The CLI and persistent RPC service must come from the same installation. The
plugin prefers the paired `sysml` and `sysml-rpc` in this virtual environment;
the automated installer also writes both absolute paths into Vim's config.
Full parser details and limitations are in [the parser integration guide](lsp-parser.md).

## Automated full install on macOS

With Homebrew installed, this one-line command clones sysml-vim into Vim's package directory and runs its installer:

```sh
brew install git && mkdir -p "$HOME/.vim/pack/plugins/start" && git clone https://github.com/michaellrowley/sysml-vim "$HOME/.vim/pack/plugins/start/sysml-vim" && "$HOME/.vim/pack/plugins/start/sysml-vim/tools/install.sh"
```

The installer uses Homebrew for missing Git, Python 3.11+, Node.js 20+, npm, Vim, or Graphviz (`dot`) dependencies; installs and builds the `sysml-v2-lsp` flow-projection branch; creates a dedicated Python virtual environment; activates the plugin without replacing an existing checkout; and adds an idempotent configuration include to `~/.vimrc`. Set `SYSML_LSP_PACKAGE_SPEC` to a full commit ref when a reproducible parser snapshot is required. Restart Vim after it completes. For an existing checkout, run `./tools/install.sh` from its root.

## Vim (vim-plug)

```vim
Plug 'michaellrowley/sysml-vim'
```

Install the Python package and language server as described above, then ensure
the editor uses both executables from the same virtual environment. The
installer generates this configuration automatically. For a manual setup:

```vim
let g:sysml_backend_cmd = expand('~/.local/share/sysml-vim/venv/bin/sysml')
let g:sysml_rpc_cmd = expand('~/.local/share/sysml-vim/venv/bin/sysml-rpc')
let $SYSML_LSP_SERVER = expand('~/.local/share/sysml-vim/lsp/node_modules/sysml-v2-lsp/dist/server/server.js')
```

If you use a custom `SYSML_VIM_INSTALL_ROOT` or `XDG_DATA_HOME`, update these
paths to match that installation.

## Neovim (lazy.nvim)

```lua
{
  "michaellrowley/sysml-vim",
  config = function()
    local data_home = vim.env.XDG_DATA_HOME or vim.fn.expand("~/.local/share")
    local install_root = vim.env.SYSML_VIM_INSTALL_ROOT or (data_home .. "/sysml-vim")
    require("sysml").setup({
      backend_cmd = install_root .. "/venv/bin/sysml",
      rpc_cmd = install_root .. "/venv/bin/sysml-rpc",
    })
    vim.env.SYSML_LSP_SERVER = install_root
      .. "/lsp/node_modules/sysml-v2-lsp/dist/server/server.js"
  end,
}
```

Install the same Python and Node dependencies as for Vim. The CLI, RPC
executable, and LSP path above all resolve under the same installation root.

## Vim native packages

Clone into `~/.vim/pack/vendor/start/sysml-vim` (or the Neovim equivalent), then run `./tools/install.sh` from that checkout.

## Graphviz for SVG

Graphviz is only required for SVG rendering. The automated macOS installer
installs it if `dot` is missing. For manual installations, use the package manager for your operating system:

- macOS: `brew install graphviz`
- Debian/Ubuntu: `sudo apt-get install graphviz`

Verify the installation with `dot -V`.
