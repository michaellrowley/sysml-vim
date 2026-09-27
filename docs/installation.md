# Installation

## Backend CLI

```bash
python -m pip install -e .
```

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
python3 -m pip install -e /path/to/sysml-vim
export SYSML_PILOT_HOME="$HOME/SysML-v2-Pilot-Implementation"
export SYSML_PILOT_COMMAND="python3 /path/to/sysml-vim/tools/sysml-pilot-bridge/run.py"
sysml health
sysml check /path/to/sysml-vim/tests/fixtures/workspace
```

The launcher discovers the `*-all.jar` and `sysml.library` inside `SYSML_PILOT_HOME`, compiles the bridge to the user's cache directory, and runs the official parser. If the JAR or library is elsewhere, set `SYSML_PILOT_JAR` and/or `SYSML_PILOT_LIBRARY`. For the alternative one-request JSON-RPC transport, set `SYSML_PILOT_RPC_COMMAND` to the same launcher instead of setting `SYSML_PILOT_COMMAND`.

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
