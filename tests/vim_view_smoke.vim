set nocompatible
let s:repository_root = getcwd()
execute 'set runtimepath^=' . fnameescape(s:repository_root)
filetype plugin on
source plugin/sysml.vim

let $PYTHONPATH = s:repository_root . '/src' . (empty($PYTHONPATH) ? '' : ':' . $PYTHONPATH)
let $SYSML_LSP_COMMAND = 'python3 ' . shellescape(s:repository_root . '/tests/fixtures/mock_lsp_server.py')
let $SYSML_LSP_SERVER = ''
let g:sysml_rpc_cmd = exepath('sysml-rpc')
let g:sysml_rpc_timeout_ms = 10000
let g:sysml_view_refresh_delay_ms = 100
let s:workspace = s:repository_root . '/tests/fixtures/workspace'
let s:source_file = s:workspace . '/vehicle.sysml'

execute 'edit ' . fnameescape(s:source_file)
execute 'lcd ' . fnameescape(s:workspace)
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

let s:workspace_b = tempname()
call mkdir(s:workspace_b, 'p')
let s:second_source_file = s:workspace_b . '/links.sysml'
call writefile(
      \ readfile(s:repository_root . '/tests/fixtures/workspace/links.sysml', 'b'),
      \ s:second_source_file,
      \ 'b'
      \ )
execute 'tabnew ' . fnameescape(s:second_source_file)
execute 'lcd ' . fnameescape(s:workspace_b)
let s:second_source_buffer = bufnr('%')
call append(line('$') - 1, '  part def DraftFromWorkspaceB;')
call sysml#tree()
let s:second_tree_buffer = bufnr('%')
if bufname('%') !=# 'sysml-tree-' . s:second_source_buffer || winnr('$') != 1
  cquit 9
endif
if tabpagenr('$') != 5
  cquit 10
endif

call win_gotoid(win_findbuf(s:source_buffer)[0])
call append(line('$') - 1, '  part def UpdateFromWorkspaceA;')
doautocmd TextChanged
sleep 20m

call win_gotoid(win_findbuf(s:second_source_buffer)[0])
call append(line('$') - 1, '  part def UpdateFromWorkspaceB;')
doautocmd TextChanged
sleep 500m

if join(getbufline(s:tree_buffer, 1, '$'), "\n") !~# 'UpdateFromWorkspaceA'
  cquit 12
endif
if join(getbufline(s:second_tree_buffer, 1, '$'), "\n") !~# 'UpdateFromWorkspaceB'
  cquit 13
endif

call delete(s:workspace_b, 'rf')
quitall!
