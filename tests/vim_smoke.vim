set nocompatible
set runtimepath^=.
source plugin/sysml.vim
if !exists(':SysmlCheck')
  cquit 1
endif
if !exists(':SysmlView')
  cquit 1
endif
if !exists(':SysmlGraph')
  cquit 1
endif
if !exists(':SysmlRelationships')
  cquit 1
endif
if !exists(':SysmlRequirements')
  cquit 1
endif
if !exists(':SysmlTraceability')
  cquit 1
endif

let $PYTHONPATH = getcwd() . '/src' . (empty($PYTHONPATH) ? '' : ':' . $PYTHONPATH)
let $SYSML_LSP_COMMAND = 'python3 ' . shellescape(getcwd() . '/tests/fixtures/mock_lsp_server.py')
let $SYSML_LSP_SERVER = ''
let g:sysml_rpc_cmd = exepath('sysml-rpc')
if empty(g:sysml_rpc_cmd)
  cquit 4
endif
let g:sysml_rpc_timeout_ms = 10000
let s:fixture_workspace = getcwd() . '/tests/fixtures/workspace'
call sysml#check(s:fixture_workspace)
if empty(getqflist())
  cquit 2
endif
call sysml#graph('Vehicle')
if bufname('%') !~# '^sysml-graph-'
  cquit 3
endif
if tabpagenr('$') != 2 || winnr('$') != 1
  cquit 5
endif
call sysml#graph('Vehicle')
if bufname('%') !~# '^sysml-graph-'
  cquit 6
endif

quitall!
