setlocal indentexpr=GetSysmlIndent()
setlocal indentkeys=o,O,0{,0},0],0)

function! GetSysmlIndent() abort
  let lnum = prevnonblank(v:lnum - 1)
  if lnum <= 0
    return 0
  endif
  let ind = indent(lnum)
  let pline = getline(lnum)
  if pline =~ '{\s*$'
    let ind += shiftwidth()
  endif
  if getline(v:lnum) =~ '^\s*}'
    let ind -= shiftwidth()
  endif
  return ind < 0 ? 0 : ind
endfunction
