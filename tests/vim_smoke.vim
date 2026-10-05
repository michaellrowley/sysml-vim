set nocompatible
set runtimepath^=.
source plugin/sysml.vim
if !exists(':V2') || !exists(':V2g') || !exists(':V2h') || !exists(':V2c')
      \ || !exists(':V2cw') || !exists(':V2d') || !exists(':V2f')
      \ || !exists(':V2hea') || !exists(':V2ho') || !exists(':V2l')
      \ || !exists(':V2r') || !exists(':V2rel') || !exists(':V2req')
      \ || !exists(':V2res') || !exists(':V2tra') || !exists(':V2t')
      \ || !exists(':V2v')
  cquit 1
endif
if !exists(':SysmlCheck')
  cquit 2
endif
if !exists(':SysmlView')
  cquit 2
endif
if !exists(':SysmlGraph')
  cquit 2
endif
if !exists(':SysmlRelationships')
  cquit 2
endif
if !exists(':SysmlRequirements')
  cquit 2
endif
if !exists(':SysmlTraceability')
  cquit 2
endif

let $PYTHONPATH = getcwd() . '/src' . (empty($PYTHONPATH) ? '' : ':' . $PYTHONPATH)
let $SYSML_LSP_COMMAND = 'python3 ' . shellescape(getcwd() . '/tests/fixtures/mock_lsp_server.py')
let $SYSML_LSP_SERVER = ''
let g:sysml_backend_cmd = $SYSML_VIM_INSTALL_ROOT . '/venv/bin/sysml'
let g:sysml_rpc_cmd = $SYSML_VIM_INSTALL_ROOT . '/venv/bin/sysml-rpc'
if !executable(g:sysml_backend_cmd) || !executable(g:sysml_rpc_cmd)
  cquit 4
endif
let g:sysml_rpc_timeout_ms = 10000
let s:fixture_workspace = getcwd() . '/tests/fixtures/workspace'
call feedkeys(':v2 check ' . fnameescape(s:fixture_workspace) . "\<CR>", 'xt')
if empty(getqflist())
  cquit 2
endif
silent! cclose
execute 'edit ' . fnameescape(s:fixture_workspace . '/vehicle.sysml')
call sysml#check()
if !empty(filter(getqflist(), 'v:val.text ==# "diagnostic from unsaved buffer"'))
  cquit 7
endif
call append('$', 'SYSML_VIM_UNSAVED_CHECK')
call sysml#check()
if empty(filter(getqflist(), 'v:val.text ==# "diagnostic from unsaved buffer"'))
  cquit 8
endif
call sysml#check_workspace(s:fixture_workspace)
if empty(filter(getqflist(), 'v:val.text ==# "diagnostic from unsaved buffer"'))
  cquit 9
endif
call feedkeys(":v2g Ygkahzr\<CR>", 'xt')
if bufname('%') !~# '^sysml-graph-'
  cquit 3
endif
if tabpagenr('$') != 2 || winnr('$') != 1
  cquit 5
endif
call feedkeys(":v2 graph Ygkahzr\<CR>", 'xt')
if bufname('%') !~# '^sysml-graph-'
  cquit 6
endif
call feedkeys(":v2h\<CR>", 'xt')
if &filetype !=# 'help'
  cquit 7
endif
call feedkeys(":v2 help\<CR>", 'xt')
if &filetype !=# 'help'
  cquit 8
endif
call feedkeys(":v2\<CR>", 'xt')
if &filetype !=# 'help'
  cquit 9
endif

execute 'lcd ' . fnameescape(s:fixture_workspace)
call feedkeys(":v2cw\<CR>", 'xt')
if empty(getqflist())
  cquit 10
endif

quitall!
