set nocompatible
set runtimepath^=.
filetype plugin on
source plugin/sysml.vim

let $PYTHONPATH = getcwd() . '/src' . (empty($PYTHONPATH) ? '' : ':' . $PYTHONPATH)
let $SYSML_LSP_COMMAND = 'python3 ' . shellescape(getcwd() . '/tests/fixtures/mock_lsp_server.py')
let $SYSML_LSP_SERVER = ''
let g:sysml_rpc_cmd = exepath('sysml-rpc')
let g:sysml_rpc_timeout_ms = 10000
let g:sysml_view_refresh_delay_ms = 100
let s:source_file = getcwd() . '/tests/fixtures/workspace/vehicle.sysml'
let s:workspace = fnamemodify(s:source_file, ':h')

execute 'edit ' . fnameescape(s:source_file)
if &filetype !=# 'sysml'
  setfiletype sysml
endif
if &l:foldlevel != 99 || foldclosed(2) != -1
  cquit 1
endif

let s:source_buffer = bufnr('%')
call append(line('$') - 1, '  part def DraftOnly;')
call sysml#tree()
let s:tree_buffer = bufnr('%')
if bufname('%') !~# '^sysml-tree-' || winnr('$') != 1
  cquit 2
endif
if join(getline(1, '$'), "\n") !~# 'DraftOnly'
  cquit 3
endif
if tabpagenr('$') != 2
  cquit 4
endif

tabprevious
if bufnr('%') != s:source_buffer
  cquit 5
endif
call append(line('$') - 1, '  part def LiveUpdate;')
doautocmd TextChanged
sleep 500m
if join(getbufline(s:tree_buffer, 1, '$'), "\n") !~# 'LiveUpdate'
  cquit 6
endif

call sysml#graph('DraftOnly')
if bufname('%') !~# '^sysml-graph-' || winnr('$') != 1
  cquit 7
endif
if join(getline(1, '$'), "\n") !~# 'DraftOnly:part_def'
  cquit 8
endif

tabfirst
call cursor(1, 1)
call sysml#graph()
if join(getline(1, '$'), "\n") !~# 'Vehicle:part_def'
  cquit 11
endif

let s:second_source_file = getcwd() . '/tests/fixtures/workspace/links.sysml'
execute 'tabnew ' . fnameescape(s:second_source_file)
let s:second_source_buffer = bufnr('%')
call sysml#tree()
if bufname('%') !=# 'sysml-tree-' . s:second_source_buffer || winnr('$') != 1
  cquit 9
endif
if tabpagenr('$') != 5
  cquit 10
endif

quitall!
