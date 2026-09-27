let s:last_log = []

function! s:sysml_word() abort
  return expand('<cword>')
endfunction

function! s:workspace_root() abort
  if exists('*getcwd')
    return getcwd()
  endif
  return '.'
endfunction

function! s:run_sync(args) abort
  let cmd = [g:sysml_backend_cmd] + a:args
  let output = systemlist(cmd)
  let status = v:shell_error
  if status != 0 && empty(output)
    call add(s:last_log, 'command failed: ' . string(cmd))
  endif
  return {'status': status, 'lines': output, 'cmd': cmd}
endfunction

function! s:run_async(args, callback) abort
  if exists('*job_start')
    let cmd = [g:sysml_backend_cmd] + a:args
    let out = []
    let job_opts = {
          \ 'out_cb': {j,d -> add(out, d)},
          \ 'err_cb': {j,d -> add(s:last_log, d)},
          \ 'exit_cb': {j,c -> call(a:callback, [c, out])}
          \ }
    call job_start(cmd, job_opts)
    return 1
  endif
  return 0
endfunction

function! s:json_decode_lines(lines) abort
  let text = join(a:lines, "\n")
  if empty(text)
    return {}
  endif
  try
    return json_decode(text)
  catch
    call add(s:last_log, 'JSON decode error: ' . text)
    return {}
  endtry
endfunction

function! s:open_result_buffer(name, lines) abort
  botright new
  execute 'file ' . a:name
  setlocal buftype=nofile bufhidden=wipe nobuflisted noswapfile
  call setline(1, a:lines)
endfunction

function! s:set_qf(diagnostics) abort
  let qf = []
  for d in a:diagnostics
    call add(qf, {
          \ 'filename': d.file,
          \ 'lnum': d.range.line,
          \ 'col': d.range.col + 1,
          \ 'text': d.message,
          \ 'type': d.severity ==# 'error' ? 'E' : 'W'
          \ })
  endfor
  call setqflist(qf, 'r')
  if len(qf) > 0
    cwindow
  endif
endfunction

function! sysml#check(...) abort
  let path = a:0 > 0 ? a:1 : expand('%:p')
  let args = ['check', path]
  if s:run_async(args, {code, out -> execute('call sysml#_handle_check(' . string(code) . ',' . string(out) . ')')})
    return
  endif
  let res = s:run_sync(args)
  call sysml#_handle_check(res.status, res.lines)
endfunction

function! sysml#_handle_check(code, lines) abort
  let payload = s:json_decode_lines(a:lines)
  if has_key(payload, 'diagnostics')
    call s:set_qf(payload.diagnostics)
    echom printf('sysml: %d diagnostics', len(payload.diagnostics))
  elseif a:code != 0
    echohl ErrorMsg | echom 'sysml check failed' | echohl None
  else
    echom 'sysml: no diagnostics'
  endif
endfunction

function! sysml#check_workspace(...) abort
  let path = a:0 > 0 ? a:1 : s:workspace_root()
  call sysml#check(path)
endfunction

function! sysml#tree(...) abort
  let path = a:0 > 0 ? a:1 : s:workspace_root()
  let res = s:run_sync(['tree', path])
  let payload = s:json_decode_lines(res.lines)
  let lines = ['SysML Tree: ' . get(payload, 'root', path), '']
  for [file, symbols] in items(get(payload, 'files', {}))
    call add(lines, file)
    for sym in symbols
      call add(lines, printf('  - %s [%s] (line %d)', sym.name, sym.kind, sym.line))
    endfor
  endfor
  call s:open_result_buffer('sysml-tree', lines)
endfunction

function! sysml#view(...) abort
  let type = a:0 > 0 ? a:1 : g:sysml_default_view
  let focus = a:0 > 1 ? a:2 : ''
  let args = ['view', type, '--path', s:workspace_root(), '--format', 'text']
  if !empty(focus)
    call extend(args, ['--focus', focus])
  endif
  let res = s:run_sync(args)
  call s:open_result_buffer('sysml-view-' . type, res.lines)
endfunction

function! sysml#find(...) abort
  let kind = a:0 > 0 ? a:1 : 'part'
  let name = a:0 > 1 ? a:2 : ''
  let args = ['query', kind, '--path', s:workspace_root()]
  if !empty(name)
    call extend(args, ['--name', name])
  endif
  let res = s:run_sync(args)
  let payload = s:json_decode_lines(res.lines)
  let qf = []
  for it in payload
    call add(qf, {'filename': it.file, 'lnum': it.range.line, 'col': it.range.col + 1, 'text': printf('%s [%s]', it.name, it.kind)})
  endfor
  call setqflist(qf, 'r')
  copen
endfunction

function! sysml#definition(...) abort
  let name = a:0 > 0 && !empty(a:1) ? a:1 : s:sysml_word()
  let res = s:run_sync(['definition', name, '--path', s:workspace_root()])
  let payload = s:json_decode_lines(res.lines)
  if empty(payload)
    echohl WarningMsg | echom 'No definition: ' . name | echohl None
    return
  endif
  execute 'edit ' . fnameescape(payload.file)
  call cursor(payload.range.line, payload.range.col + 1)
endfunction

function! sysml#references(...) abort
  let name = a:0 > 0 && !empty(a:1) ? a:1 : s:sysml_word()
  let res = s:run_sync(['references', name, '--path', s:workspace_root()])
  let payload = s:json_decode_lines(res.lines)
  let qf = []
  for it in payload
    call add(qf, {'filename': it.file, 'lnum': it.range.line, 'col': it.range.col + 1, 'text': get(it, 'relation', 'reference') . ': ' . name})
  endfor
  call setqflist(qf, 'r')
  copen
endfunction

function! sysml#hover(...) abort
  let name = a:0 > 0 && !empty(a:1) ? a:1 : s:sysml_word()
  let res = s:run_sync(['hover', name, '--path', s:workspace_root()])
  let payload = s:json_decode_lines(res.lines)
  if empty(payload)
    echom 'No hover info for ' . name
    return
  endif
  let lines = [payload.name . ' [' . payload.kind . ']']
  if has_key(payload, 'signature') && !empty(payload.signature)
    call add(lines, payload.signature)
  endif
  if has_key(payload, 'location')
    call add(lines, payload.location.file . ':' . payload.location.line)
  endif
  call s:open_result_buffer('sysml-hover', lines)
endfunction

function! sysml#relationships(...) abort
  let focus = a:0 > 0 ? a:1 : s:sysml_word()
  call sysml#view('dependencies', focus)
endfunction

function! sysml#requirements(...) abort
  let focus = a:0 > 0 ? a:1 : s:sysml_word()
  call sysml#view('requirements', focus)
endfunction

function! sysml#traceability(...) abort
  let focus = a:0 > 0 ? a:1 : s:sysml_word()
  call sysml#view('traceability', focus)
endfunction

function! sysml#complete(findstart, base) abort
  if a:findstart
    let line = getline('.')
    let start = col('.') - 1
    while start > 0 && line[start - 1] =~ '\k'
      let start -= 1
    endwhile
    return start
  endif
  let res = s:run_sync(['completion', a:base, '--path', s:workspace_root()])
  let payload = s:json_decode_lines(res.lines)
  return map(payload, {_, v -> {'word': v.label, 'menu': '[' . v.kind . ']'}})
endfunction

function! sysml#health() abort
  let res = s:run_sync(['health', '--path', s:workspace_root()])
  call s:open_result_buffer('sysml-health', res.lines)
endfunction

function! sysml#restart() abort
  echom 'sysml backend uses one-shot commands; nothing to restart'
endfunction

function! sysml#log() abort
  if empty(s:last_log)
    echom 'sysml log is empty'
    return
  endif
  call s:open_result_buffer('sysml-log', s:last_log)
endfunction
