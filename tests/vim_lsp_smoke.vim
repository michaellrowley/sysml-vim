set nocompatible
execute 'set runtimepath^=' . fnameescape(getcwd())
source plugin/sysml.vim

if !exists(':SysmlCheck') || !exists(':SysmlGraph')
  cquit 1
endif

let $PYTHONPATH = getcwd() . '/src' . (empty($PYTHONPATH) ? '' : ':' . $PYTHONPATH)
let g:sysml_rpc_cmd = exepath('sysml-rpc')
if empty(g:sysml_rpc_cmd)
  cquit 7
endif
let g:sysml_rpc_timeout_ms = 10000
let s:workspace = getcwd() . '/tests/fixtures/lsp'
execute 'lcd ' . fnameescape(s:workspace)
call sysml#check(s:workspace)
if !empty(filter(getqflist(), 'v:val.valid && v:val.type ==# "E"'))
  cquit 2
endif

call sysml#graph('Vehicle')
if bufname('%') !~# '^sysml-graph-'
  cquit 3
endif
if tabpagenr('$') != 2 || winnr('$') != 1
  cquit 6
endif
if join(getline(1, '$'), "\n") !~# 'Vehicle:part_def'
  cquit 4
endif

call sysml#graph('Vehicle')
if bufname('%') !~# '^sysml-graph-'
  cquit 5
endif

quitall!
