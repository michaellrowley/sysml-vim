set nocompatible
set runtimepath^=.

let s:windows = has('win32') || has('win64')
let s:bin_directory = s:windows ? '/venv/Scripts' : '/venv/bin'
let s:suffix = s:windows ? '.exe' : ''
let s:install_root = tempname()
let $SYSML_VIM_INSTALL_ROOT = s:install_root
unlet! g:sysml_backend_cmd g:sysml_rpc_cmd
source plugin/sysml.vim

if g:sysml_backend_cmd !=# s:install_root . s:bin_directory . '/sysml' . s:suffix
      \ || g:sysml_rpc_cmd !=# s:install_root . s:bin_directory . '/sysml-rpc' . s:suffix
  cquit 1
endif

let s:data_home = tempname()
let s:install_root = s:data_home . '/sysml-vim'
let $SYSML_VIM_INSTALL_ROOT = ''
let $XDG_DATA_HOME = s:data_home
unlet g:loaded_sysml_vim
unlet! g:sysml_backend_cmd g:sysml_rpc_cmd
source plugin/sysml.vim

if g:sysml_backend_cmd !=# s:install_root . s:bin_directory . '/sysml' . s:suffix
      \ || g:sysml_rpc_cmd !=# s:install_root . s:bin_directory . '/sysml-rpc' . s:suffix
  cquit 2
endif

let s:custom_bin = tempname() . '/bin'
let $SYSML_VIM_INSTALL_ROOT = ''
let $XDG_DATA_HOME = ''
unlet g:loaded_sysml_vim
unlet! g:sysml_backend_cmd g:sysml_rpc_cmd
let g:sysml_backend_cmd = s:custom_bin . '/sysml'
source plugin/sysml.vim

if g:sysml_rpc_cmd !=# s:custom_bin . '/sysml-rpc'
  cquit 3
endif

qa!
