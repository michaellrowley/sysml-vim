#!/usr/bin/env bash
set -euo pipefail

readonly PILOT_REPOSITORY="https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation.git"
readonly PILOT_JAR_PATTERN="org.omg.sysml.interactive-*-all.jar"

fail() {
  printf 'sysml-vim installer: %s\n' "$1" >&2
  exit 1
}

python_is_supported() {
  command -v python3 >/dev/null 2>&1 &&
    python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'
}

java_is_supported() {
  command -v java >/dev/null 2>&1 || return 1
  command -v javac >/dev/null 2>&1 || return 1

  local runtime_major compiler_major
  runtime_major=$(java -version 2>&1 | awk -F '"' 'NR == 1 { split($2, version, "."); print version[1] }')
  compiler_major=$(javac -version 2>&1 | awk '{ split($2, version, "."); print version[1] }')
  [[ "$runtime_major" =~ ^[0-9]+$ && "$compiler_major" =~ ^[0-9]+$ ]] || return 1
  (( runtime_major >= 21 && compiler_major >= 21 ))
}

if [[ "${1:-}" == "--help" ]]; then
  cat <<'HELP'
Install the SysML v2 Pilot, the sysml-vim Python backend, and the Vim plugin.

Run this script from a sysml-vim checkout. Homebrew is used on macOS to install
missing Git, Python 3.11+, Java 21+, or Vim dependencies.

Overrides:
  SYSML_VIM_INSTALL_ROOT  data and Python environment directory
  SYSML_VIM_PLUGIN_DIR    Vim package install location
  SYSML_PILOT_HOME        existing or desired Pilot checkout
HELP
  exit 0
fi

[[ $# -eq 0 ]] || fail "unknown argument: $1 (use --help)"

source_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
[[ -f "$source_root/pyproject.toml" ]] || fail "run this script from a sysml-vim checkout"

brew_packages=()
command -v git >/dev/null 2>&1 || brew_packages+=(git)
python_is_supported || brew_packages+=(python@3.12)
java_is_supported || brew_packages+=(openjdk@21)
command -v vim >/dev/null 2>&1 || brew_packages+=(vim)

if (( ${#brew_packages[@]} > 0 )); then
  command -v brew >/dev/null 2>&1 || fail "install Homebrew to provide missing prerequisites: ${brew_packages[*]}"
  brew install "${brew_packages[@]}"
  homebrew_prefix=$(brew --prefix)
  export PATH="$homebrew_prefix/bin:$homebrew_prefix/sbin:$PATH"

  if ! python_is_supported; then
    python_prefix=$(brew --prefix python@3.12)
    export PATH="$python_prefix/bin:$PATH"
  fi
  if ! java_is_supported; then
    jdk_prefix=$(brew --prefix openjdk@21)
    jdk_home="$jdk_prefix/libexec/openjdk.jdk/Contents/Home"
    [[ -x "$jdk_home/bin/java" ]] || fail "Homebrew's openjdk@21 installation is incomplete"
    export JAVA_HOME="$jdk_home"
    export PATH="$JAVA_HOME/bin:$jdk_prefix/bin:$PATH"
  fi
fi

command -v git >/dev/null 2>&1 || fail "git is required"
python_is_supported || fail "Python 3.11 or newer is required"
java_is_supported || fail "a Java 21 or newer JDK (java and javac) is required"
command -v vim >/dev/null 2>&1 || fail "Vim is required"

home_directory=${HOME:?HOME must be set}
install_root=${SYSML_VIM_INSTALL_ROOT:-"$home_directory/.local/share/sysml-vim"}
mkdir -p "$install_root"
install_root=$(cd "$install_root" && pwd -P)

pilot_home=${SYSML_PILOT_HOME:-"$install_root/SysML-v2-Pilot-Implementation"}
case "$pilot_home" in
  /*) ;;
  *) pilot_home="$PWD/$pilot_home" ;;
esac
mkdir -p "$(dirname "$pilot_home")"
if [[ ! -f "$pilot_home/mvnw" ]]; then
  if [[ -d "$pilot_home" ]] && [[ -n "$(find "$pilot_home" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
    fail "Pilot directory exists but is not a Pilot checkout: $pilot_home"
  fi
  printf 'Cloning the official SysML v2 Pilot into %s\n' "$pilot_home"
  git clone "$PILOT_REPOSITORY" "$pilot_home"
fi
pilot_home=$(cd "$pilot_home" && pwd -P)

shopt -s nullglob
pilot_jars=("$pilot_home/org.omg.sysml.interactive/target/"$PILOT_JAR_PATTERN)
if [[ ! -d "$pilot_home/sysml.library" ]] || (( ${#pilot_jars[@]} != 1 )); then
  printf 'Building the official Pilot and its model library; this can take several minutes.\n'
  (cd "$pilot_home" && ./mvnw clean install)
fi
pilot_jars=("$pilot_home/org.omg.sysml.interactive/target/"$PILOT_JAR_PATTERN)
[[ -d "$pilot_home/sysml.library" ]] || fail "Pilot model library is missing after the build"
(( ${#pilot_jars[@]} == 1 )) || fail "expected one Pilot interactive *-all.jar after the build"

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

java_bin=$(command -v java)
javac_bin=$(command -v javac)
path_prefix="$virtual_environment/bin:$(dirname "$java_bin"):$(dirname "$javac_bin")"
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
  printf "let \$SYSML_PILOT_HOME = '%s'\n" "$(vim_quote "$pilot_home")"
  printf "let \$SYSML_PILOT_COMMAND = '%s'\n" "$(vim_quote "$virtual_environment/bin/sysml-pilot-bridge")"
  printf "let \$SYSML_PILOT_RPC_COMMAND = '%s'\n" "$(vim_quote "$virtual_environment/bin/sysml-pilot-bridge")"
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
printf 'Pilot: %s\n' "$pilot_home"
if (( load_source_root_first )); then
  printf 'Vim plugin: %s (runtimepath; preserved existing checkout at %s)\n' \
    "$source_root" "$plugin_directory"
else
  printf 'Vim plugin: %s\n' "$plugin_directory"
fi
printf 'Vim configuration: %s\n' "$vim_configuration"
printf 'Restart Vim, then run :SysmlGraph or :SysmlCheck.\n'
