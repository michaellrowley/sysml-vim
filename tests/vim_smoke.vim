set nocompatible
set runtimepath^=.
source plugin/sysml.vim
if !exists(':SysmlCheck')
  cquit 1
endif
if !exists(':SysmlView')
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
quitall!
