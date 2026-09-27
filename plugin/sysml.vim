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

nnoremap <silent> <Plug>(sysml-definition) :SysmlDefinition<CR>
nnoremap <silent> <Plug>(sysml-references) :SysmlReferences<CR>
nnoremap <silent> <Plug>(sysml-hover) :SysmlHover<CR>
nnoremap <silent> <Plug>(sysml-next-diagnostic) ]d
nnoremap <silent> <Plug>(sysml-prev-diagnostic) [d

if !hasmapto('<Plug>(sysml-definition)')
  nmap gd <Plug>(sysml-definition)
endif
if !hasmapto('<Plug>(sysml-references)')
  nmap gr <Plug>(sysml-references)
endif
if !hasmapto('<Plug>(sysml-hover)')
  nmap K <Plug>(sysml-hover)
endif
