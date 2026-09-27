let s:last_log = []
let s:rpc_job = 0
let s:rpc_seq = 0
let s:view_sessions = {}
let s:view_refresh_timer = -1
let s:view_refresh_paths = {}

function! s:sysml_word() abort
  return expand('<cword>')
endfunction

function! s:workspace_root() abort
  if exists('*getcwd')
    return getcwd()
  endif
  return '.'
endfunction

function! s:rpc_cmd() abort
  if exists('g:sysml_rpc_cmd')
    return g:sysml_rpc_cmd
  endif
  return 'sysml-rpc'
endfunction

function! s:rpc_enabled() abort
  if !exists('g:sysml_use_rpc')
    let g:sysml_use_rpc = 1
  endif
  return g:sysml_use_rpc && exists('*job_start') && exists('*ch_sendraw') && exists('*ch_read')
endfunction

function! s:ensure_rpc_job() abort
  if !s:rpc_enabled()
    return 0
  endif
  " Vim uses Job objects; Neovim's compatibility API can return numeric IDs.
  if type(s:rpc_job) == v:t_number
    if s:rpc_job > 0 && job_status(s:rpc_job) ==# 'run'
      return 1
    endif
  elseif job_status(s:rpc_job) ==# 'run'
    return 1
  endif
  let cmd = [s:rpc_cmd()]
  let opts = {
        \ 'in_mode': 'nl',
        \ 'out_mode': 'nl',
        \ 'err_cb': {j,d -> add(s:last_log, d)}
        \ }
  let s:rpc_job = job_start(cmd, opts)
  if type(s:rpc_job) == v:t_number && (s:rpc_job == 0 || s:rpc_job == -1)
    call add(s:last_log, 'failed to start rpc backend: ' . string(cmd))
    let s:rpc_job = 0
    return 0
  endif
  return 1
endfunction

function! s:rpc_request(method, params) abort
  if !s:ensure_rpc_job()
    return {'ok': v:false}
  endif
  let chan = job_getchannel(s:rpc_job)
  let s:rpc_seq += 1
  let id = s:rpc_seq
  let req = {'jsonrpc': '2.0', 'id': id, 'method': a:method, 'params': a:params}
  call ch_sendraw(chan, json_encode(req) . "\n")
  let timeout = get(g:, 'sysml_rpc_timeout_ms', 120000)
  let line = ch_read(chan, {'timeout': timeout})
  if empty(line)
    call add(s:last_log, 'rpc timeout: ' . a:method)
    return {'ok': v:false}
  endif
  try
    let resp = json_decode(line)
  catch
    call add(s:last_log, 'rpc decode failed: ' . line)
    return {'ok': v:false}
  endtry
  if has_key(resp, 'error')
    call add(s:last_log, 'rpc error: ' . get(resp.error, 'message', 'unknown'))
    return {'ok': v:false, 'error': resp.error}
  endif
  return {'ok': v:true, 'result': get(resp, 'result', {})}
endfunction

function! s:run_sync(args) abort
  let cmd = [g:sysml_backend_cmd] + a:args
  if has('nvim')
    let output = systemlist(cmd)
  else
    let output = systemlist(join(map(copy(cmd), 'shellescape(v:val)'), ' '))
  endif
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
  let existing_buffer = bufnr(a:name)
  if bufname('%') ==# a:name
    " Reuse the visible result buffer instead of reopening its existing name.
  elseif existing_buffer >= 0
    execute 'botright sbuffer ' . existing_buffer
  else
    botright new
    execute 'file ' . fnameescape(a:name)
  endif
  setlocal buftype=nofile bufhidden=wipe nobuflisted noswapfile
  setlocal modifiable
  silent! %delete _
  call setline(1, empty(a:lines) ? [''] : a:lines)
endfunction

function! s:active_view_context() abort
  let session_key = string(bufnr('%'))
  if has_key(s:view_sessions, session_key)
    let session = s:view_sessions[session_key]
    return {
          \ 'source_buffer': session.source_buffer,
          \ 'path': session.path,
          \ 'focus': get(session, 'focus', '')
          \ }
  endif
  return {'source_buffer': bufnr('%'), 'path': s:workspace_root(), 'focus': ''}
endfunction

function! s:is_model_file(file_path) abort
  return a:file_path =~? '\.\(sysml\|kerml\)$'
endfunction

function! s:path_is_in_workspace(file_path, workspace_path) abort
  let resolved_file = resolve(fnamemodify(a:file_path, ':p'))
  let resolved_workspace = resolve(fnamemodify(a:workspace_path, ':p'))
  if resolved_file ==# resolved_workspace
    return 1
  endif
  let workspace_prefix = substitute(resolved_workspace, '[/\\]\+$', '', '') . '/'
  return stridx(resolved_file, workspace_prefix) == 0
endfunction

function! s:workspace_documents(workspace_path, preferred_buffer) abort
  let documents_by_path = {}
  let has_modified_buffers = 0
  let workspace_buffers = getbufinfo({'bufloaded': 1})

  " Add other modified workspace files first so the active source buffer wins on duplicates.
  for preferred_pass in [0, 1]
    for buffer_info in workspace_buffers
      let buffer_number = buffer_info.bufnr
      let is_preferred_buffer = buffer_number == a:preferred_buffer
      if is_preferred_buffer != preferred_pass
        continue
      endif
      if empty(buffer_info.name)
        continue
      endif
      let file_path = resolve(fnamemodify(buffer_info.name, ':p'))
      if !s:is_model_file(file_path)
        continue
      endif
      if !s:path_is_in_workspace(file_path, a:workspace_path)
        continue
      endif
      let has_unsaved_changes = getbufvar(buffer_number, '&modified')
      if !is_preferred_buffer && !has_unsaved_changes
        continue
      endif
      let buffer_lines = getbufline(buffer_number, 1, '$')
      let documents_by_path[file_path] = {
            \ 'path': file_path,
            \ 'text': join(empty(buffer_lines) ? [''] : buffer_lines, "\n")
            \ }
      if has_unsaved_changes
        let has_modified_buffers = 1
      endif
    endfor
  endfor

  return {
        \ 'documents': values(documents_by_path),
        \ 'has_modified_buffers': has_modified_buffers
        \ }
endfunction

function! s:view_request(session) abort
  let params = copy(a:session.params)
  let document_state = s:workspace_documents(
        \ a:session.path,
        \ a:session.source_buffer
        \ )
  if !empty(document_state.documents)
    let params.documents = document_state.documents
  endif
  let rpc = s:rpc_request(a:session.method, params)
  if !get(rpc, 'ok', v:false)
    return {
          \ 'ok': v:false,
          \ 'error': get(get(rpc, 'error', {}), 'message', 'RPC request failed'),
          \ 'has_modified_buffers': document_state.has_modified_buffers
          \ }
  endif

  let result = rpc.result
  if a:session.method ==# 'tree'
    let lines = s:tree_lines(result, a:session.path)
  elseif a:session.method ==# 'view_text'
    let lines = split(get(result, 'text', ''), "\n")
  else
    let lines = split(get(result, 'graph', ''), "\n")
  endif
  return {
        \ 'ok': v:true,
        \ 'lines': lines,
        \ 'has_modified_buffers': document_state.has_modified_buffers
        \ }
endfunction

function! s:tree_lines(tree, fallback_path) abort
  let lines = ['SysML Tree: ' . get(a:tree, 'root', a:fallback_path), '']
  for [file_path, symbols] in items(get(a:tree, 'files', {}))
    call add(lines, file_path)
    for symbol in symbols
      call add(lines, printf('  - %s [%s] (line %d)', symbol.name, symbol.kind, symbol.line))
    endfor
  endfor
  return lines
endfunction

function! s:open_model_view(buffer_name, method, path, params, fallback_args) abort
  let context = s:active_view_context()
  let session = {
        \ 'source_buffer': context.source_buffer,
        \ 'path': a:path,
        \ 'method': a:method,
        \ 'focus': get(a:params, 'focus', ''),
        \ 'params': copy(a:params)
        \ }
  let view_response = s:view_request(session)
  if get(view_response, 'ok', v:false)
    let lines = view_response.lines
  elseif get(view_response, 'has_modified_buffers', v:false)
    echohl ErrorMsg
    echom 'sysml view failed; unsaved SysML text requires a working RPC backend: ' . view_response.error
    echohl None
    return
  else
    let command_result = s:run_sync(a:fallback_args)
    if command_result.status != 0 && empty(command_result.lines)
      echohl ErrorMsg
      echom 'sysml view command failed'
      echohl None
      return
    endif
    if a:method ==# 'tree'
      let tree_result = s:json_decode_lines(command_result.lines)
      if !has_key(tree_result, 'files')
        echohl ErrorMsg
        echom 'sysml tree command returned invalid data'
        echohl None
        return
      endif
      let lines = s:tree_lines(tree_result, a:path)
    else
      let lines = command_result.lines
    endif
  endif
  call s:open_view_buffer(a:buffer_name, lines, session)
endfunction

function! s:replace_buffer_lines(buffer_number, lines) abort
  let replacement_lines = empty(a:lines) ? [''] : a:lines
  let previous_line_count = len(getbufline(a:buffer_number, 1, '$'))
  call setbufline(a:buffer_number, 1, replacement_lines)
  if previous_line_count > len(replacement_lines) && exists('*deletebufline')
    call deletebufline(a:buffer_number, len(replacement_lines) + 1, previous_line_count)
  endif
  call setbufvar(a:buffer_number, '&modified', 0)
endfunction

function! s:open_view_buffer(name, lines, session) abort
  let buffer_name = a:name . '-' . a:session.source_buffer
  let view_buffer = bufnr(buffer_name)
  if view_buffer >= 0
    let view_windows = win_findbuf(view_buffer)
    if !empty(view_windows)
      let target_window = view_windows[0]
      let tab_and_window = win_id2tabwin(target_window)
      call win_gotoid(target_window)
      if len(tabpagebuflist(tab_and_window[0])) > 1
        tab split
      endif
    else
      tabnew
      execute 'buffer ' . view_buffer
    endif
  else
    tabnew
    execute 'file ' . fnameescape(buffer_name)
    let view_buffer = bufnr('%')
  endif

  setlocal buftype=nofile bufhidden=wipe nobuflisted noswapfile
  setlocal modifiable
  call s:replace_buffer_lines(bufnr('%'), a:lines)
  let s:view_sessions[string(bufnr('%'))] = copy(a:session)
  let b:sysml_source_buffer = a:session.source_buffer
  let b:sysml_workspace_path = a:session.path
endfunction

function! sysml#_schedule_view_refresh(source_buffer) abort
  if empty(s:view_sessions) || !bufexists(a:source_buffer)
    return
  endif
  let changed_path = bufname(a:source_buffer)
  if empty(changed_path) || !s:is_model_file(changed_path)
    return
  endif
  " A shared debounce timer must retain paths from every workspace it replaces.
  let s:view_refresh_paths[resolve(fnamemodify(changed_path, ':p'))] = 1
  if s:view_refresh_timer >= 0
    call timer_stop(s:view_refresh_timer)
  endif
  if exists('*timer_start')
    let delay = get(g:, 'sysml_view_refresh_delay_ms', 500)
    let s:view_refresh_timer = timer_start(
          \ delay,
          \ function('sysml#_refresh_views')
          \ )
  else
    call sysml#_refresh_views(-1)
  endif
endfunction

function! sysml#_refresh_views(timer_id) abort
  let changed_paths = keys(s:view_refresh_paths)
  let s:view_refresh_paths = {}
  let s:view_refresh_timer = -1
  if empty(changed_paths)
    return
  endif

  for session_key in keys(copy(s:view_sessions))
    let session = s:view_sessions[session_key]
    let result_buffer = str2nr(session_key)
    if !bufexists(result_buffer)
      call remove(s:view_sessions, session_key)
      continue
    endif
    let workspace_changed = 0
    for changed_path in changed_paths
      if s:path_is_in_workspace(changed_path, session.path)
        let workspace_changed = 1
        break
      endif
    endfor
    if !workspace_changed
      continue
    endif
    let refreshed_view = s:view_request(session)
    if !get(refreshed_view, 'ok', v:false)
      echohl WarningMsg
      echom 'sysml view refresh failed: ' . refreshed_view.error
      echohl None
      continue
    endif
    call s:replace_buffer_lines(result_buffer, refreshed_view.lines)
  endfor
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
  let rpc = s:rpc_request('check', {'path': path})
  if get(rpc, 'ok', v:false)
    call sysml#_handle_check(0, [json_encode(rpc.result)])
    return
  endif

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
  call s:open_model_view('sysml-tree', 'tree', path, {'path': path}, ['tree', path])
endfunction

function! sysml#view(...) abort
  let type = a:0 > 0 ? a:1 : g:sysml_default_view
  let focus = a:0 > 1 ? a:2 : ''
  let context = s:active_view_context()
  let params = {'path': context.path, 'type': type}
  if !empty(focus)
    let params.focus = focus
  endif
  let args = ['view', type, '--path', context.path, '--format', 'text']
  if !empty(focus)
    call extend(args, ['--focus', focus])
  endif
  call s:open_model_view('sysml-view-' . type, 'view_text', context.path, params, args)
endfunction

function! sysml#graph(...) abort
  let context = s:active_view_context()
  let focus = a:0 > 0 ? a:1 : context.focus
  if empty(focus)
    let focus = ''
  endif

  let params = {'path': context.path, 'type': 'composition', 'depth': 5}
  if !empty(focus)
    let params.focus = focus
  endif
  let args = ['view', 'composition', '--path', context.path, '--format', 'graph', '--depth', '5']
  if !empty(focus)
    call extend(args, ['--focus', focus])
  endif
  call s:open_model_view('sysml-graph', 'view_graph', context.path, params, args)
endfunction

function! sysml#find(...) abort
  let kind = a:0 > 0 ? a:1 : 'part'
  let name = a:0 > 1 ? a:2 : ''
  let payload = []
  let rpc_params = {'path': s:workspace_root(), 'kind': kind}
  if !empty(name)
    let rpc_params.name = name
  endif
  let rpc = s:rpc_request('query', rpc_params)
  if get(rpc, 'ok', v:false)
    let payload = rpc.result
  else
    let args = ['query', kind, '--path', s:workspace_root()]
    if !empty(name)
      call extend(args, ['--name', name])
    endif
    let res = s:run_sync(args)
    let payload = s:json_decode_lines(res.lines)
  endif
  let qf = []
  for it in payload
    call add(qf, {'filename': it.file, 'lnum': it.range.line, 'col': it.range.col + 1, 'text': printf('%s [%s]', it.name, it.kind)})
  endfor
  call setqflist(qf, 'r')
  copen
endfunction

function! sysml#definition(...) abort
  let name = a:0 > 0 && !empty(a:1) ? a:1 : s:sysml_word()
  let payload = {}
  let rpc = s:rpc_request('definition', {'path': s:workspace_root(), 'name': name})
  if get(rpc, 'ok', v:false)
    let payload = rpc.result
  else
    let res = s:run_sync(['definition', name, '--path', s:workspace_root()])
    let payload = s:json_decode_lines(res.lines)
  endif
  if empty(payload)
    echohl WarningMsg | echom 'No definition: ' . name | echohl None
    return
  endif
  execute 'keepjumps drop ' . fnameescape(payload.file)
  call cursor(payload.range.line, payload.range.col + 1)
endfunction

function! sysml#references(...) abort
  let name = a:0 > 0 && !empty(a:1) ? a:1 : s:sysml_word()
  let payload = []
  let rpc = s:rpc_request('references', {'path': s:workspace_root(), 'name': name})
  if get(rpc, 'ok', v:false)
    let payload = rpc.result
  else
    let res = s:run_sync(['references', name, '--path', s:workspace_root()])
    let payload = s:json_decode_lines(res.lines)
  endif
  let qf = []
  for it in payload
    call add(qf, {'filename': it.file, 'lnum': it.range.line, 'col': it.range.col + 1, 'text': get(it, 'relation', 'reference') . ': ' . name})
  endfor
  call setqflist(qf, 'r')
  copen
endfunction

function! sysml#hover(...) abort
  let name = a:0 > 0 && !empty(a:1) ? a:1 : s:sysml_word()
  let payload = {}
  let rpc = s:rpc_request('hover', {'path': s:workspace_root(), 'name': name})
  if get(rpc, 'ok', v:false)
    let payload = rpc.result
  else
    let res = s:run_sync(['hover', name, '--path', s:workspace_root()])
    let payload = s:json_decode_lines(res.lines)
  endif
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

  let payload = []
  let rpc = s:rpc_request('completion', {'path': s:workspace_root(), 'prefix': a:base})
  if get(rpc, 'ok', v:false)
    let payload = rpc.result
  else
    let res = s:run_sync(['completion', a:base, '--path', s:workspace_root()])
    let payload = s:json_decode_lines(res.lines)
  endif
  return map(payload, {_, v -> {'word': v.label, 'menu': '[' . v.kind . ']'}})
endfunction

function! sysml#health() abort
  let rpc = s:rpc_request('health', {'path': s:workspace_root()})
  if get(rpc, 'ok', v:false)
    call s:open_result_buffer('sysml-health', split(json_encode(rpc.result), "\n"))
    return
  endif
  let res = s:run_sync(['health', '--path', s:workspace_root()])
  call s:open_result_buffer('sysml-health', res.lines)
endfunction

function! sysml#restart() abort
  if s:rpc_job != 0
    call job_stop(s:rpc_job)
    let s:rpc_job = 0
    echom 'sysml rpc backend restarted'
    return
  endif
  echom 'sysml backend uses one-shot commands; nothing to restart'
endfunction

function! sysml#log() abort
  if empty(s:last_log)
    echom 'sysml log is empty'
    return
  endif
  call s:open_result_buffer('sysml-log', s:last_log)
endfunction
