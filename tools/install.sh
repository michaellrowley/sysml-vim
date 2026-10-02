#!/usr/bin/env bash
set -euo pipefail

readonly LSP_PACKAGE_NAME="sysml-v2-lsp"
readonly DEFAULT_LSP_PACKAGE_SPEC="git+https://github.com/michaellrowley/sysml-v2-lsp.git#feat/flow-usage-projection"

fail() {
  printf 'sysml-vim installer: %s\n' "$1" >&2
  exit 1
}

python_is_supported() {
  command -v python3 >/dev/null 2>&1 &&
    python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'
}

node_is_supported() {
  command -v node >/dev/null 2>&1 &&
    node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)'
}

if [[ "${1:-}" == "--help" ]]; then
  cat <<'HELP'
Install the SysML v2 language server, the sysml-vim Python backend, and Vim plugin.

Run this script from a sysml-vim checkout. Homebrew is used on macOS to install
missing Git, Python 3.11+, Node.js 20+, Vim, or Graphviz (`dot`) dependencies.

Overrides:
  SYSML_VIM_INSTALL_ROOT  data and Python environment directory
  SYSML_VIM_PLUGIN_DIR    Vim package install location
  SYSML_LSP_PACKAGE_SPEC  npm package spec (default: the flow projection branch)
  SYSML_LSP_PACKAGE_VERSION  legacy npm-version override
HELP
  exit 0
fi

[[ $# -eq 0 ]] || fail "unknown argument: $1 (use --help)"

source_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
[[ -f "$source_root/pyproject.toml" ]] || fail "run this script from a sysml-vim checkout"

brew_packages=()
command -v git >/dev/null 2>&1 || brew_packages+=(git)
python_is_supported || brew_packages+=(python@3.12)
if ! node_is_supported || ! command -v npm >/dev/null 2>&1; then
  brew_packages+=(node)
fi
command -v vim >/dev/null 2>&1 || brew_packages+=(vim)
command -v dot >/dev/null 2>&1 || brew_packages+=(graphviz)

if (( ${#brew_packages[@]} > 0 )); then
  command -v brew >/dev/null 2>&1 || fail "install Homebrew to provide missing prerequisites: ${brew_packages[*]}"
  brew install "${brew_packages[@]}"
  homebrew_prefix=$(brew --prefix)
  export PATH="$homebrew_prefix/bin:$homebrew_prefix/sbin:$PATH"

  if ! python_is_supported; then
    python_prefix=$(brew --prefix python@3.12)
    export PATH="$python_prefix/bin:$PATH"
  fi
fi

python_is_supported || fail "Python 3.11 or newer is required"
node_is_supported || fail "Node.js 20 or newer is required"
command -v npm >/dev/null 2>&1 || fail "npm is required to install the SysML language server"
command -v git >/dev/null 2>&1 || fail "Git is required to install the SysML language server from GitHub"
command -v vim >/dev/null 2>&1 || fail "Vim is required"

home_directory=${HOME:?HOME must be set}
install_root=${SYSML_VIM_INSTALL_ROOT:-"$home_directory/.local/share/sysml-vim"}
mkdir -p "$install_root"
install_root=$(cd "$install_root" && pwd -P)

lsp_home="$install_root/lsp"
lsp_package_spec=${SYSML_LSP_PACKAGE_SPEC:-}
if [[ -z "$lsp_package_spec" ]]; then
  lsp_package_spec=$DEFAULT_LSP_PACKAGE_SPEC
  if [[ -n "${SYSML_LSP_PACKAGE_VERSION:-}" ]]; then
    lsp_package_spec="$LSP_PACKAGE_NAME@$SYSML_LSP_PACKAGE_VERSION"
  fi
fi
mkdir -p "$lsp_home"
printf 'Installing %s from %s into %s\n' "$LSP_PACKAGE_NAME" "$lsp_package_spec" "$lsp_home"
npm install \
  --prefix "$lsp_home" \
  --no-save \
  --no-package-lock \
  --no-audit \
  --no-fund \
  "$lsp_package_spec"
lsp_server="$lsp_home/node_modules/$LSP_PACKAGE_NAME/dist/server/server.js"
[[ -f "$lsp_server" ]] || fail "the installed package does not contain its LSP server entry point"

plugin_directory=${SYSML_VIM_PLUGIN_DIR:-"$home_directory/.vim/pack/plugins/start/sysml-vim"}
plugin_parent=$(dirname "$plugin_directory")
plugin_name=$(basename "$plugin_directory")
mkdir -p "$plugin_parent"
plugin_directory="$(cd "$plugin_parent" && pwd -P)/$plugin_name"
load_source_root_first=0
if [[ -e "$plugin_directory" || -L "$plugin_directory" ]]; then
  [[ -d "$plugin_directory" ]] || fail "Vim plugin destination is not a directory: $plugin_directory"
  existing_plugin=$(cd "$plugin_directory" && pwd -P)
  if [[ "$existing_plugin" != "$source_root" ]]; then
    load_source_root_first=1
    printf 'Preserving the existing plugin checkout; Vim will load this checkout first.\n'
  fi
else
  ln -s "$source_root" "$plugin_directory"
fi

virtual_environment="$install_root/venv"
if [[ ! -x "$virtual_environment/bin/python" ]]; then
  python3 -m venv "$virtual_environment"
fi
"$virtual_environment/bin/python" -m pip install --editable "$source_root"

path_prefix="$virtual_environment/bin:$(dirname "$(command -v node)")"
if command -v dot >/dev/null 2>&1; then
  path_prefix="$path_prefix:$(dirname "$(command -v dot)")"
fi

vim_directory="$home_directory/.vim"
mkdir -p "$vim_directory"
vim_configuration="$vim_directory/sysml-vim.vim"
vimrc="$home_directory/.vimrc"
vim_quote() {
  printf '%s' "$1" | sed "s/'/''/g"
}

{
  printf 'set nocompatible\n'
  if (( load_source_root_first )); then
    printf "let &runtimepath = '%s' . ',' . &runtimepath\n" "$(vim_quote "$source_root")"
  fi
  printf "let \$PATH = '%s' . ':' . \$PATH\n" "$(vim_quote "$path_prefix")"
  printf "let \$SYSML_LSP_SERVER = '%s'\n" "$(vim_quote "$lsp_server")"
  printf "let g:sysml_backend_cmd = '%s'\n" "$(vim_quote "$virtual_environment/bin/sysml")"
  printf "let g:sysml_rpc_cmd = '%s'\n" "$(vim_quote "$virtual_environment/bin/sysml-rpc")"
  printf 'let g:sysml_use_rpc = 1\n'
  printf 'let g:sysml_rpc_timeout_ms = 120000\n'
} > "$vim_configuration"

source_statement="execute 'source ' . fnameescape(expand('~/.vim/sysml-vim.vim'))"
touch "$vimrc"
if ! grep -Fqx "$source_statement" "$vimrc"; then
  printf '\n" sysml-vim parser and backend configuration\n%s\n' "$source_statement" >> "$vimrc"
fi

printf '\nInstallation complete.\n'
printf 'Parser: %s from %s\n' "$LSP_PACKAGE_NAME" "$lsp_package_spec"
if (( load_source_root_first )); then
  printf 'Vim plugin: %s (runtimepath; preserved existing checkout at %s)\n' \
    "$source_root" "$plugin_directory"
else
  printf 'Vim plugin: %s\n' "$plugin_directory"
fi
printf 'Vim configuration: %s\n' "$vim_configuration"
printf 'Restart Vim, then run :SysmlGraph or :SysmlCheck.\n'
