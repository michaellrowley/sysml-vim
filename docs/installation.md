# Installation

## Backend CLI

```bash
python -m pip install -e .
```

Installing the editor plugin and Python package does not install the official SysML v2 parser. Complete the parser setup below before running model-dependent commands, including graph and semantic views.

## Automated full install on macOS

With Homebrew installed, this one-line command clones sysml-vim into Vim's native package directory and runs its installer:

```sh
brew install git && mkdir -p "$HOME/.vim/pack/plugins/start" && git clone https://github.com/michaellrowley/sysml-vim "$HOME/.vim/pack/plugins/start/sysml-vim" && "$HOME/.vim/pack/plugins/start/sysml-vim/tools/install.sh"
```

The installer uses Homebrew for missing Git, Python 3.11+, Java 21+, or Vim dependencies; clones and builds the official Pilot if needed; installs sysml-vim into a dedicated Python virtual environment; activates the plugin in Vim without replacing an existing checkout; and adds an idempotent configuration include to `~/.vimrc`. Restart Vim after it completes. A fresh Pilot build can take several minutes. If sysml-vim is already checked out, run `./tools/install.sh` from its root instead.

## SysML v2 parser and validator

Every model-reading operation uses the included Java bridge to the official [SysML v2 Pilot Implementation](https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation). The bridge needs the Pilot's shaded `org.omg.sysml.interactive-*-all.jar`; the launcher compiles the small bridge source against that JAR on first use. You do not need to write or obtain a separate adapter.

Build the Pilot using its Maven wrapper and Java 21:

```bash
git clone https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation.git
cd SysML-v2-Pilot-Implementation
./mvnw clean install
```

The Eclipse Modeling Tools IDE is optional for this command-line build. The first build downloads Maven and the Pilot's dependencies. It produces the parser JAR under `org.omg.sysml.interactive/target/`.

Point sysml-vim at that checkout and its included bridge, then install the Python backend:

```bash
python3 -m pip install -e .
export SYSML_PILOT_HOME="$HOME/SysML-v2-Pilot-Implementation"
export SYSML_PILOT_COMMAND="sysml-pilot-bridge"
sysml health
sysml check tests/fixtures/workspace
```

Installing the Python package also installs the `sysml-pilot-bridge` command into that Python environment; activate it or add its `bin`/`Scripts` directory to `PATH` before launching Vim/Neovim. The bridge discovers the `*-all.jar` and `sysml.library` inside `SYSML_PILOT_HOME`, compiles into the user's cache directory, and runs the official parser. If the JAR or library is elsewhere, set `SYSML_PILOT_JAR` and/or `SYSML_PILOT_LIBRARY`. For the alternative one-request JSON-RPC transport, set `SYSML_PILOT_RPC_COMMAND=sysml-pilot-bridge` instead of setting `SYSML_PILOT_COMMAND`.

`sysml health` reports configuration but does not launch Java; `sysml check` exercises the parser. Vim/Neovim must inherit these environment variables when started. There is no local subset parser or fallback.

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
