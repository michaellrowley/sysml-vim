set nocompatible

if !exists(':SysmlCheck') || !exists(':SysmlGraph')
  cquit 1
endif

let s:workspace = getcwd() . '/tests/fixtures/lsp'
call sysml#check(s:workspace)
if !empty(filter(getqflist(), 'v:val.valid && v:val.type ==# "E"'))
  cquit 2
endif

call sysml#graph('Vehicle')
if bufname('%') !=# 'sysml-graph'
  cquit 3
endif
if join(getline(1, '$'), "\n") !~# 'Vehicle:part_def'
  cquit 4
endif

call sysml#graph('Vehicle')
if bufname('%') !=# 'sysml-graph'
  cquit 5
endif

quitall!
