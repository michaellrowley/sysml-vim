if exists('g:loaded_sysml_vim')
  finish
endif
let g:loaded_sysml_vim = 1

if !exists('g:sysml_backend_cmd')
  let g:sysml_backend_cmd = 'sysml'
endif
if !exists('g:sysml_default_view')
  let g:sysml_default_view = 'composition'
endif
if !exists('g:sysml_use_rpc')
  let g:sysml_use_rpc = 1
endif
if !exists('g:sysml_rpc_cmd')
  let g:sysml_rpc_cmd = 'sysml-rpc'
endif

command! -nargs=* V2 call sysml#command(<f-args>)
command! -nargs=? V2g call sysml#graph(<f-args>)
command! -nargs=0 V2h call sysml#help()
command! -nargs=? V2c call sysml#check(<f-args>)
command! -nargs=? V2cw call sysml#check_workspace(<f-args>)
command! -nargs=? V2d call sysml#definition(<f-args>)
command! -nargs=* V2f call sysml#find(<f-args>)
command! -nargs=0 V2hea call sysml#health()
command! -nargs=? V2ho call sysml#hover(<f-args>)
command! -nargs=0 V2l call sysml#log()
command! -nargs=? V2r call sysml#references(<f-args>)
command! -nargs=? V2rel call sysml#relationships(<f-args>)
command! -nargs=? V2req call sysml#requirements(<f-args>)
command! -nargs=0 V2res call sysml#restart()
command! -nargs=? V2tra call sysml#traceability(<f-args>)
command! -nargs=? V2t call sysml#tree(<f-args>)
command! -nargs=* V2v call sysml#view(<f-args>)

function! s:define_command_abbreviation(alias, command) abort
  if !empty(maparg(a:alias, 'c'))
    return
  endif
  execute 'cnoreabbrev <expr> ' . a:alias
        \ . ' getcmdtype() ==# ' . string(':')
        \ . ' && getcmdline() ==# ' . string(a:alias)
        \ . ' ? ' . string(a:command) . ' : ' . string(a:alias)
endfunction

let s:command_aliases = [
      \ ['v2', 'V2'],
      \ ['v2g', 'V2g'],
      \ ['v2h', 'V2h'],
      \ ['v2c', 'V2c'],
      \ ['v2cw', 'V2cw'],
      \ ['v2d', 'V2d'],
      \ ['v2f', 'V2f'],
      \ ['v2hea', 'V2hea'],
      \ ['v2ho', 'V2ho'],
      \ ['v2l', 'V2l'],
      \ ['v2r', 'V2r'],
      \ ['v2rel', 'V2rel'],
      \ ['v2req', 'V2req'],
      \ ['v2res', 'V2res'],
      \ ['v2tra', 'V2tra'],
      \ ['v2t', 'V2t'],
      \ ['v2v', 'V2v']
      \ ]
for alias in s:command_aliases
  call s:define_command_abbreviation(alias[0], alias[1])
endfor
unlet s:command_aliases

" Keep the original commands as compatibility aliases.
command! -nargs=? SysmlCheck call sysml#check(<f-args>)
command! -nargs=? SysmlCheckWorkspace call sysml#check_workspace(<f-args>)
command! -nargs=* SysmlView call sysml#view(<f-args>)
command! -nargs=? SysmlGraph call sysml#graph(<f-args>)
command! -nargs=? SysmlTree call sysml#tree(<f-args>)
command! -nargs=* SysmlFind call sysml#find(<f-args>)
command! -nargs=? SysmlDefinition call sysml#definition(<f-args>)
command! -nargs=? SysmlReferences call sysml#references(<f-args>)
command! -nargs=? SysmlHover call sysml#hover(<f-args>)
command! -nargs=? SysmlRelationships call sysml#relationships(<f-args>)
command! -nargs=? SysmlRequirements call sysml#requirements(<f-args>)
command! -nargs=? SysmlTraceability call sysml#traceability(<f-args>)
command! -nargs=0 SysmlHealth call sysml#health()
command! -nargs=0 SysmlLog call sysml#log()
command! -nargs=0 SysmlRestart call sysml#restart()

augroup sysml_view_sync
  autocmd!
  autocmd TextChanged,TextChangedI,BufWritePost *.sysml,*.kerml call sysml#_schedule_view_refresh(bufnr('%'))
augroup END

augroup sysml_graph_resize
  autocmd!
  if exists('##WinResized')
    autocmd WinResized * call sysml#_schedule_graph_reflow()
  endif
  if exists('##WinClosed')
    autocmd WinClosed * call sysml#_schedule_graph_reflow()
  endif
augroup END

nnoremap <silent> <Plug>(sysml-definition) :V2 definition<CR>
nnoremap <silent> <Plug>(sysml-references) :V2 references<CR>
nnoremap <silent> <Plug>(sysml-hover) :V2 hover<CR>
nnoremap <silent> <Plug>(sysml-next-diagnostic) ]d
nnoremap <silent> <Plug>(sysml-prev-diagnostic) [d
nnoremap <silent> <Plug>(sysml-graph-next-node) :call sysml#graph_navigate('node', 1)<CR>
nnoremap <silent> <Plug>(sysml-graph-prev-node) :call sysml#graph_navigate('node', -1)<CR>
nnoremap <silent> <Plug>(sysml-graph-next-edge) :call sysml#graph_navigate('edge', 1)<CR>
nnoremap <silent> <Plug>(sysml-graph-prev-edge) :call sysml#graph_navigate('edge', -1)<CR>
nnoremap <silent> <Plug>(sysml-graph-left) :call sysml#graph_move('left')<CR>
nnoremap <silent> <Plug>(sysml-graph-right) :call sysml#graph_move('right')<CR>
nnoremap <silent> <Plug>(sysml-graph-up) :call sysml#graph_move('up')<CR>
nnoremap <silent> <Plug>(sysml-graph-down) :call sysml#graph_move('down')<CR>
nnoremap <silent> <Plug>(sysml-graph-mouse) :call sysml#graph_mouse_sync('mouse')<CR>

if !hasmapto('<Plug>(sysml-definition)')
  nmap gd <Plug>(sysml-definition)
endif
if !hasmapto('<Plug>(sysml-references)')
  nmap gr <Plug>(sysml-references)
endif
if !hasmapto('<Plug>(sysml-hover)')
  nmap K <Plug>(sysml-hover)
endif
