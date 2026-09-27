setlocal commentstring=//\ %s
setlocal omnifunc=sysml#complete
setlocal foldmethod=expr
setlocal foldexpr=SysmlFoldLevel(v:lnum)
setlocal foldlevel=99

function! SysmlFoldLevel(lnum) abort
  let level = 0
  for i in range(1, a:lnum - 1)
    let line = getline(i)
    let level += len(split(line, '{')) - 1
    let level -= len(split(line, '}')) - 1
  endfor
  let current = getline(a:lnum)
  if current =~ '^\s*}'
    let level -= 1
  endif
  return level < 0 ? 0 : level + 1
endfunction
