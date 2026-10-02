let s:last_log = []
let s:rpc_job = 0
let s:rpc_seq = 0
let s:view_sessions = {}
let s:view_refresh_timer = -1
let s:view_refresh_paths = {}
let s:graph_buffers = {}
let s:graph_reflow_timer = -1
let s:graph_mousemove_original = -1
let s:graph_mousemove_changed = 0

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
  let graph_layout = {}
  if a:session.method ==# 'tree'
    let lines = s:tree_lines(result, a:session.path)
  elseif a:session.method ==# 'view_text'
    let lines = split(get(result, 'text', ''), "\n")
  else
    let lines = split(get(result, 'graph', ''), "\n")
    let graph_layout = get(result, 'layout', {})
  endif
  return {
        \ 'ok': v:true,
        \ 'lines': lines,
        \ 'layout': graph_layout,
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
    if a:method ==# 'view_graph'
      let session.graph_layout = view_response.layout
    endif
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
    elseif a:method ==# 'view_graph'
      let graph_result = s:json_decode_lines(command_result.lines)
      if !has_key(graph_result, 'graph') || !has_key(graph_result, 'layout')
        echohl ErrorMsg
        echom 'sysml graph command returned invalid diagram data'
        echohl None
        return
      endif
      let lines = split(graph_result.graph, "\n")
      let session.graph_layout = graph_result.layout
    else
      let lines = command_result.lines
    endif
  endif
  call s:open_view_buffer(a:buffer_name, lines, session)
endfunction

function! s:replace_buffer_lines(buffer_number, lines, graph_layout) abort
  let replacement_lines = empty(a:lines) ? [''] : a:lines
  let previous_line_count = len(getbufline(a:buffer_number, 1, '$'))
  call setbufline(a:buffer_number, 1, replacement_lines)
  call setbufvar(a:buffer_number, 'sysml_graph_layout', a:graph_layout)
  if previous_line_count > len(replacement_lines) && exists('*deletebufline')
    call deletebufline(a:buffer_number, len(replacement_lines) + 1, previous_line_count)
  endif
  call setbufvar(a:buffer_number, '&modified', 0)
  if getbufvar(a:buffer_number, 'sysml_view_method', '') ==# 'view_graph'
        \ && exists('*win_execute')
    for window_id in win_findbuf(a:buffer_number)
      call win_execute(window_id, 'call sysml#_refresh_graph_highlights()')
    endfor
  endif
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
  call s:replace_buffer_lines(
        \ bufnr('%'),
        \ a:lines,
        \ get(a:session, 'graph_layout', {})
        \ )
  let s:view_sessions[string(bufnr('%'))] = copy(a:session)
  let b:sysml_source_buffer = a:session.source_buffer
  let b:sysml_workspace_path = a:session.path
  let b:sysml_view_method = a:session.method
  if a:session.method ==# 'view_graph'
    setlocal nocursorline
    setlocal nowrap sidescroll=1
    if get(get(a:session, 'graph_layout', {}), 'presentation', '') ==# 'browser'
      setlocal foldmethod=indent shiftwidth=2 foldlevel=99 foldenable
    else
      setlocal nofoldenable
    endif
    call s:setup_graph_buffer()
    call s:graph_apply_styles()
    if empty(maparg(']n', 'n'))
      nmap <buffer> ]n <Plug>(sysml-graph-next-node)
    endif
    if empty(maparg('[n', 'n'))
      nmap <buffer> [n <Plug>(sysml-graph-prev-node)
    endif
    if empty(maparg(']e', 'n'))
      nmap <buffer> ]e <Plug>(sysml-graph-next-edge)
    endif
    if empty(maparg('[e', 'n'))
      nmap <buffer> [e <Plug>(sysml-graph-prev-edge)
    endif
    if empty(maparg('<CR>', 'n'))
      nmap <buffer> <CR> <Plug>(sysml-graph-inspect)
    endif
    call s:select_graph_node(get(a:session, 'focus', ''))
  endif
endfunction

function! s:graph_nodes() abort
  let nodes = []
  " The emitted box label identifies each node and its hit-test bounds.
  for line_number in range(1, line('$'))
    let text = getline(line_number)
    let search_from = 0
    let left_border = stridx(text, '│', search_from)
    while left_border >= 0
      let label_start = left_border + strlen('│') + 1
      let right_border = stridx(text, '│', label_start)
      if right_border < 0
        break
      endif
      let label = trim(strpart(text, label_start, right_border - label_start))
      let separator = stridx(label, ':')
      if separator > 0
        call add(nodes, {
              \ 'name': trim(strpart(label, 0, separator)),
              \ 'kind': trim(strpart(label, separator + 1)),
              \ 'line': line_number,
              \ 'col': label_start + 1,
              \ 'top': line_number - 1,
              \ 'bottom': line_number + 1,
              \ 'left': strdisplaywidth(strpart(text, 0, left_border)) + 1,
              \ 'right': strdisplaywidth(strpart(text, 0, right_border)) + 1,
              \ 'left_col': left_border + 1,
              \ 'right_col': right_border + 1
              \ })
      endif
      let search_from = right_border + strlen('│')
      let left_border = stridx(text, '│', search_from)
    endwhile
  endfor
  return nodes
endfunction

function! s:graph_positions(kind) abort
  let positions = []
  if a:kind ==# 'node'
    for node in s:graph_layout().nodes
      call add(positions, [node.line, node.col])
    endfor
    return positions
  endif

  let in_edges = 0
  for line_number in range(1, line('$'))
    let text = getline(line_number)
    if text ==# 'Edges:'
      let in_edges = 1
    elseif in_edges && text =~# '^- '
      let edge_start = match(text, '- \zs\S')
      if edge_start >= 0
        call add(positions, [line_number, edge_start + 1])
      endif
    endif
  endfor
  return positions
endfunction

function! s:graph_edges(nodes) abort
  let nodes_by_name = {}
  for node in a:nodes
    let nodes_by_name[node.name] = node
  endfor

  let edges = []
  let in_edges = 0
  for line_number in range(1, line('$'))
    let text = getline(line_number)
    if text ==# 'Edges:'
      let in_edges = 1
      continue
    endif
    if !in_edges || text !~# '^- '
      continue
    endif

    let edge_text = strpart(text, 2)
    let relation_start = stridx(edge_text, ' -[')
    if relation_start < 0
      continue
    endif
    let relation_end = stridx(edge_text, ']-> ', relation_start + 3)
    if relation_end < 0
      continue
    endif
    let source_name = trim(strpart(edge_text, 0, relation_start))
    let relation = strpart(edge_text, relation_start + 3, relation_end - relation_start - 3)
    let target_name = trim(strpart(edge_text, relation_end + 4))
    if !has_key(nodes_by_name, source_name) || !has_key(nodes_by_name, target_name)
      continue
    endif

    let source = nodes_by_name[source_name]
    let target = nodes_by_name[target_name]
    let box_width = source.right - source.left + 1
    " Mirror the renderer's midpoint routing to map pointer hits to visible edges.
    let start_x = source.left - 1 + box_width
    let end_x = target.left - 2
    let mid_x = (start_x + end_x) / 2

    let edge_start = match(text, '- \zs\S')
    call add(edges, {
          \ 'source': source_name,
          \ 'target': target_name,
          \ 'relation': relation,
          \ 'line': line_number,
          \ 'col': edge_start + 1,
          \ 'source_line': source.line,
          \ 'target_line': target.line,
          \ 'start_x': start_x,
          \ 'end_x': end_x,
          \ 'mid_x': mid_x
          \ })
  endfor
  return edges
endfunction

function! s:edge_contains(edge, line_number, column) abort
  if has_key(a:edge, 'route_cells')
    for position in a:edge.route_cells
      if position[0] == a:line_number && position[1] == a:column
        return 1
      endif
    endfor
    return 0
  endif
  if a:line_number == a:edge.source_line
        \ && a:column >= a:edge.start_x + 1
        \ && a:column <= a:edge.mid_x
    return 1
  endif
  if a:line_number >= min([a:edge.source_line, a:edge.target_line])
        \ && a:line_number <= max([a:edge.source_line, a:edge.target_line])
        \ && a:column == a:edge.mid_x + 1
    return 1
  endif
  return a:line_number == a:edge.target_line
        \ && a:column >= a:edge.mid_x + 1
        \ && a:column <= a:edge.end_x + 1
endfunction

function! s:graph_layout() abort
  " Mouse movement is frequent; buffer refresh invalidates this parsed layout.
  if !exists('b:sysml_graph_layout') || empty(b:sysml_graph_layout)
    let nodes = s:graph_nodes()
    let b:sysml_graph_layout = {'nodes': nodes, 'edges': s:graph_edges(nodes)}
  endif
  return b:sysml_graph_layout
endfunction

function! s:setup_graph_highlight_groups() abort
  highlight default link SysmlGraphNodeStructure Type
  highlight default link SysmlGraphNodeInterface Special
  highlight default link SysmlGraphNodeBehavior Statement
  highlight default link SysmlGraphNodeRequirement Todo
  highlight default link SysmlGraphNodeOther Comment
  highlight default link SysmlGraphEdgeRoute SpecialKey
  highlight default link SysmlGraphEdgeContainment Identifier
  highlight default link SysmlGraphEdgeTyping Type
  highlight default link SysmlGraphEdgeDerivation PreProc
  highlight default link SysmlGraphEdgeRequirement Todo
  highlight default link SysmlGraphEdgeDependency Special
  highlight default link SysmlGraphEdgeOther Comment
  highlight default link SysmlGraphJunction WarningMsg
  highlight default link SysmlGraphSelection Visual
endfunction

function! s:graph_node_highlight(kind) abort
  if a:kind =~# 'requirement\|verification\|satisfaction'
    return 'SysmlGraphNodeRequirement'
  elseif a:kind =~# 'port\|interface\|connection'
    return 'SysmlGraphNodeInterface'
  elseif a:kind =~# 'action\|state\|transition\|behavior'
    return 'SysmlGraphNodeBehavior'
  elseif a:kind =~# 'part\|item\|attribute\|package\|classifier\|occurrence'
    return 'SysmlGraphNodeStructure'
  endif
  return 'SysmlGraphNodeOther'
endfunction

function! s:graph_edge_highlight(relation) abort
  if a:relation =~# 'contain\|member\|owned'
    return 'SysmlGraphEdgeContainment'
  elseif a:relation =~# 'satisf\|verif\|trace\|refin'
    return 'SysmlGraphEdgeRequirement'
  elseif a:relation =~# 'specializ\|redefin\|subset\|union\|intersect'
    return 'SysmlGraphEdgeDerivation'
  elseif a:relation =~# 'type\|typing'
    return 'SysmlGraphEdgeTyping'
  elseif a:relation =~# 'depend\|allocat'
    return 'SysmlGraphEdgeDependency'
  endif
  return 'SysmlGraphEdgeOther'
endfunction

function! s:graph_add_cell(cells, line_number, display_column) abort
  let line_key = string(a:line_number)
  if !has_key(a:cells, line_key)
    let a:cells[line_key] = {}
  endif
  let a:cells[line_key][string(a:display_column)] = 1
endfunction

function! s:graph_add_route_cell(cells, seen, line_number, display_column) abort
  let key = a:line_number . ':' . a:display_column
  if !has_key(a:seen, key)
    let a:seen[key] = 1
    call add(a:cells, [a:line_number, a:display_column])
  endif
endfunction

function! s:graph_route_cells(edge) abort
  let cells = []
  let seen = {}
  if has_key(a:edge, 'route_cells')
    for position in a:edge.route_cells
      call s:graph_add_route_cell(cells, seen, position[0], position[1])
    endfor
    return cells
  endif
  if a:edge.start_x < a:edge.mid_x
    for x in range(a:edge.start_x, a:edge.mid_x - 1)
      call s:graph_add_route_cell(cells, seen, a:edge.source_line, x + 1)
    endfor
  endif

  for line_number in range(
        \ min([a:edge.source_line, a:edge.target_line]),
        \ max([a:edge.source_line, a:edge.target_line]))
    call s:graph_add_route_cell(cells, seen, line_number, a:edge.mid_x + 1)
  endfor

  if a:edge.mid_x < a:edge.end_x
    for x in range(a:edge.mid_x, a:edge.end_x - 1)
      call s:graph_add_route_cell(cells, seen, a:edge.target_line, x + 1)
    endfor
  endif
  call s:graph_add_route_cell(cells, seen, a:edge.target_line, a:edge.end_x + 1)
  return cells
endfunction

function! s:graph_byte_column(line_number, display_column) abort
  let text = getline(a:line_number)
  let byte_column = 1
  let display_column = 1
  let character_index = 0
  while byte_column <= strlen(text)
    let character = strcharpart(text, character_index, 1)
    let character_width = strdisplaywidth(character, display_column - 1)
    if character_width > 0
      if a:display_column < display_column + character_width
        return byte_column
      endif
      let display_column += character_width
    endif
    let byte_column += strlen(character)
    let character_index += 1
  endwhile
  return strlen(text) + 1
endfunction

function! s:graph_cell_positions(cells) abort
  let positions = []
  for [line_key, line_cells] in items(a:cells)
    let columns = []
    for column_key in keys(line_cells)
      call add(columns, str2nr(column_key))
    endfor
    call sort(columns, 'n')
    if empty(columns)
      continue
    endif

    let first_column = columns[0]
    let last_column = first_column
    let column_index = 1
    while column_index < len(columns)
      let column = columns[column_index]
      if column == last_column + 1
        let last_column = column
      else
        let first_byte = s:graph_byte_column(str2nr(line_key), first_column)
        let end_byte = s:graph_byte_column(str2nr(line_key), last_column + 1)
        call add(positions, [str2nr(line_key), first_byte, end_byte - first_byte])
        let first_column = column
        let last_column = column
      endif
      let column_index += 1
    endwhile
    let first_byte = s:graph_byte_column(str2nr(line_key), first_column)
    let end_byte = s:graph_byte_column(str2nr(line_key), last_column + 1)
    call add(positions, [str2nr(line_key), first_byte, end_byte - first_byte])
  endfor
  return positions
endfunction

function! s:graph_add_matches(group, positions, priority) abort
  let position_index = 0
  while position_index < len(a:positions)
    let last_index = min([position_index + 7, len(a:positions) - 1])
    let match_id = matchaddpos(
          \ a:group,
          \ a:positions[position_index : last_index],
          \ a:priority)
    call add(w:sysml_graph_style_matches, match_id)
    let position_index = last_index + 1
  endwhile
endfunction

function! s:graph_apply_styles() abort
  call s:setup_graph_highlight_groups()
  for match_id in get(w:, 'sysml_graph_style_matches', [])
    call matchdelete(match_id)
  endfor
  let w:sysml_graph_style_matches = []

  let layout = s:graph_layout()
  let positions_by_group = {}
  let cells_by_group = {}
  let overlap_counts = {}
  for node in layout.nodes
    let group = s:graph_node_highlight(node.kind)
    if !has_key(positions_by_group, group)
      let positions_by_group[group] = []
    endif
    for line_number in range(node.top, node.bottom)
      if line_number >= 1 && line_number <= line('$')
        let first_byte = s:graph_byte_column(line_number, node.left)
        let end_byte = s:graph_byte_column(line_number, node.right + 1)
        if end_byte > first_byte
          call add(positions_by_group[group], [
                \ line_number,
                \ first_byte,
                \ end_byte - first_byte
                \ ])
        endif
      endif
    endfor
  endfor

  for edge in layout.edges
    let group = s:graph_edge_highlight(edge.relation)
    if !has_key(positions_by_group, group)
      let positions_by_group[group] = []
    endif
    let edge_text = getline(edge.line)
    if !empty(edge_text)
      call add(positions_by_group[group], [edge.line, 1, strlen(edge_text)])
    endif
    if !has_key(cells_by_group, 'SysmlGraphEdgeRoute')
      let cells_by_group.SysmlGraphEdgeRoute = {}
    endif
    for cell in s:graph_route_cells(edge)
      call s:graph_add_cell(cells_by_group.SysmlGraphEdgeRoute, cell[0], cell[1])
      let key = cell[0] . ':' . cell[1]
      let overlap_counts[key] = get(overlap_counts, key, 0) + 1
    endfor
  endfor

  for [group, cells] in items(cells_by_group)
    let positions = s:graph_cell_positions(cells)
    if !has_key(positions_by_group, group)
      let positions_by_group[group] = []
    endif
    call extend(positions_by_group[group], positions)
  endfor
  let junction_cells = {}
  for [key, overlap_total] in items(overlap_counts)
    if overlap_total > 1
      let coordinates = split(key, ':')
      let line_number = str2nr(coordinates[0])
      let display_column = str2nr(coordinates[1])
      let byte_column = s:graph_byte_column(line_number, display_column)
      let character = matchstr(strpart(getline(line_number), byte_column - 1), '^.')
      if character ==# '┼'
        call s:graph_add_cell(junction_cells, line_number, display_column)
      endif
    endif
  endfor
  if !empty(junction_cells)
    let positions_by_group.SysmlGraphJunction = s:graph_cell_positions(junction_cells)
  endif

  for [group, positions] in items(positions_by_group)
    let priority = group ==# 'SysmlGraphJunction' ? 15
          \ : group =~# '^SysmlGraphNode' ? 20 : 10
    call s:graph_add_matches(group, positions, priority)
  endfor
endfunction

function! sysml#_refresh_graph_highlights() abort
  if get(b:, 'sysml_view_method', '') !=# 'view_graph'
    return
  endif
  call s:graph_apply_styles()
  call s:graph_highlight_selection()
endfunction

function! s:graph_set_cursor(line_number, column) abort
  if line('.') == a:line_number && col('.') == a:column
    return
  endif
  let b:sysml_graph_syncing = 1
  try
    call cursor(a:line_number, a:column)
  finally
    let b:sysml_graph_syncing = 0
  endtry
endfunction

function! s:graph_highlight_selection() abort
  let previous_matches = get(w:, 'sysml_graph_selection_matches', [])
  if empty(previous_matches) && exists('w:sysml_graph_selection_match')
    let previous_matches = [w:sysml_graph_selection_match]
  endif
  for match_id in previous_matches
    call matchdelete(match_id)
  endfor
  let w:sysml_graph_selection_matches = []
  unlet! w:sysml_graph_selection_match

  let selection = get(b:, 'sysml_graph_selection', {})
  let positions = []
  if get(selection, 'kind', '') ==# 'node'
    for node in s:graph_layout().nodes
      if (!empty(get(selection, 'id', '')) && node.id ==# selection.id)
            \ || (empty(get(selection, 'id', ''))
            \ && node.name ==# get(selection, 'name', ''))
        for line_number in range(node.top, node.bottom)
          let first_byte = s:graph_byte_column(line_number, node.left)
          let end_byte = s:graph_byte_column(line_number, node.right + 1)
          if end_byte > first_byte
            call add(positions, [
                  \ line_number,
                  \ first_byte,
                  \ end_byte - first_byte
                  \ ])
          endif
        endfor
        break
      endif
    endfor
  elseif get(selection, 'kind', '') ==# 'edge'
    for edge in s:graph_layout().edges
      if edge.source ==# get(selection, 'source', '')
            \ && edge.relation ==# get(selection, 'relation', '')
            \ && edge.target ==# get(selection, 'target', '')
        call add(positions, [edge.line, 1, strlen(getline(edge.line))])
        let route_cells = {}
        for cell in s:graph_route_cells(edge)
          call s:graph_add_cell(route_cells, cell[0], cell[1])
        endfor
        call extend(positions, s:graph_cell_positions(route_cells))
        break
      endif
    endfor
  endif

  if !empty(positions)
    let position_index = 0
    while position_index < len(positions)
      let last_index = min([position_index + 7, len(positions) - 1])
      let match_id = matchaddpos(
            \ 'SysmlGraphSelection',
            \ positions[position_index : last_index],
            \ 30)
      if match_id >= 0
        if empty(w:sysml_graph_selection_matches)
          let w:sysml_graph_selection_match = match_id
        endif
        call add(w:sysml_graph_selection_matches, match_id)
      endif
      let position_index = last_index + 1
    endwhile
  endif
endfunction

function! s:select_graph_node(focus) abort
  let nodes = s:graph_layout().nodes
  if empty(nodes)
    return
  endif
  if !empty(a:focus)
    for node in nodes
      if node.name ==# a:focus
        let b:sysml_graph_selection = {
              \ 'kind': 'node',
              \ 'id': node.id,
              \ 'name': node.name
              \ }
        call s:graph_highlight_selection()
        call s:graph_set_cursor(node.line, node.col)
        return
      endif
    endfor
  endif
  let b:sysml_graph_selection = {
        \ 'kind': 'node',
        \ 'id': nodes[0].id,
        \ 'name': nodes[0].name
        \ }
  call s:graph_highlight_selection()
  call s:graph_set_cursor(nodes[0].line, nodes[0].col)
endfunction

function! s:setup_graph_buffer() abort
  let buffer_number = bufnr('%')
  let buffer_key = string(buffer_number)
  if has_key(s:graph_buffers, buffer_key)
    return
  endif

  " Neovim needs this option for <MouseMove>; restore it after the last graph closes.
  if empty(s:graph_buffers) && exists('+mousemoveevent')
    let s:graph_mousemove_original = &mousemoveevent
    let s:graph_mousemove_changed = !&mousemoveevent
    if s:graph_mousemove_changed
      let &mousemoveevent = 1
    endif
  endif
  let s:graph_buffers[buffer_key] = 1
  augroup sysml_graph_navigation
    autocmd CursorMoved <buffer> call sysml#graph_mouse_sync()
    autocmd WinEnter <buffer> call sysml#_graph_window_enter()
    autocmd BufWipeout <buffer> call sysml#_graph_buffer_wiped(str2nr(expand('<abuf>')))
  augroup END

  let graph_mappings = {
        \ '<Left>': '<Plug>(sysml-graph-left)',
        \ '<Right>': '<Plug>(sysml-graph-right)',
        \ '<Up>': '<Plug>(sysml-graph-up)',
        \ '<Down>': '<Plug>(sysml-graph-down)'
        \ }
  for [key, mapping] in items(graph_mappings)
    if empty(maparg(key, 'n'))
      execute 'nmap <buffer> ' . key . ' ' . mapping
    endif
  endfor
  if exists('+mousemoveevent') && empty(maparg('<MouseMove>', 'n'))
    nmap <buffer> <MouseMove> <Plug>(sysml-graph-mouse)
  endif
endfunction

function! sysml#_graph_buffer_wiped(buffer_number) abort
  let buffer_key = string(a:buffer_number)
  if !has_key(s:graph_buffers, buffer_key)
    return
  endif
  call remove(s:graph_buffers, buffer_key)
  if empty(s:graph_buffers)
        \ && s:graph_mousemove_changed
        \ && exists('+mousemoveevent')
        \ && &mousemoveevent
    let &mousemoveevent = s:graph_mousemove_original
  endif
  let s:graph_mousemove_original = -1
  let s:graph_mousemove_changed = 0
endfunction

function! s:graph_window_width(buffer_number) abort
  let width = 0
  if exists('*getwininfo')
    for window in getwininfo()
      if window.bufnr == a:buffer_number
        let width = width == 0 ? window.width : min([width, window.width])
      endif
    endfor
  endif
  return width > 0 ? width : winwidth(0)
endfunction

function! s:reflow_graph_buffer(buffer_number) abort
  let session_key = string(a:buffer_number)
  if !has_key(s:view_sessions, session_key)
        \ || !bufexists(a:buffer_number)
        \ || getbufvar(a:buffer_number, 'sysml_view_method', '') !=# 'view_graph'
    return
  endif
  let window_ids = win_findbuf(a:buffer_number)
  if empty(window_ids)
    return
  endif

  let session = copy(s:view_sessions[session_key])
  let width = max([40, s:graph_window_width(a:buffer_number)])
  if get(session.params, 'width', 0) == width
    return
  endif
  let session.params.width = width
  let response = s:view_request(session)
  if !get(response, 'ok', v:false)
    if get(response, 'has_modified_buffers', v:false)
      echohl ErrorMsg
      echom 'sysml graph resize failed; unsaved model text requires a working RPC backend: '
            \ . get(response, 'error', 'RPC request failed')
      echohl None
      return
    endif
    let args = [
          \ 'view', 'composition', '--path', session.path,
          \ '--format', 'graph-json',
          \ '--depth', string(get(session.params, 'depth', 5)),
          \ '--width', string(width)
          \ ]
    if !empty(session.focus)
      call extend(args, ['--focus', session.focus])
    endif
    let command_result = s:run_sync(args)
    let graph_result = s:json_decode_lines(command_result.lines)
    if (command_result.status != 0 && empty(command_result.lines))
          \ || !has_key(graph_result, 'graph')
          \ || !has_key(graph_result, 'layout')
      echohl ErrorMsg
      echom 'sysml graph resize failed'
      echohl None
      return
    endif
    let response = {
          \ 'ok': v:true,
          \ 'lines': split(graph_result.graph, "\n"),
          \ 'layout': graph_result.layout
          \ }
  endif

  let selected = getbufvar(a:buffer_number, 'sysml_graph_selection', {})
  call s:replace_buffer_lines(a:buffer_number, response.lines, response.layout)
  let session.graph_layout = response.layout
  let s:view_sessions[session_key] = session

  if get(selected, 'kind', '') ==# 'node'
    for node in get(response.layout, 'nodes', [])
      if (!empty(get(selected, 'id', '')) && node.id ==# selected.id)
            \ || node.name ==# get(selected, 'name', '')
        let selected.id = node.id
        let selected.name = node.name
        call setbufvar(a:buffer_number, 'sysml_graph_selection', selected)
        if exists('*win_execute')
          for window_id in window_ids
            call win_execute(
                  \ window_id,
                  \ printf('call cursor(%d, %d)', node.line, node.col)
                  \ )
          endfor
        elseif bufnr('%') == a:buffer_number
          call cursor(node.line, node.col)
        endif
        break
      endif
    endfor
  endif
endfunction

function! sysml#_graph_window_enter() abort
  setlocal nowrap sidescroll=1
  call s:reflow_graph_buffer(bufnr('%'))
endfunction

function! sysml#_schedule_graph_reflow() abort
  if exists('*timer_start')
    if s:graph_reflow_timer >= 0
      call timer_stop(s:graph_reflow_timer)
    endif
    let s:graph_reflow_timer = timer_start(
          \ 50,
          \ function('sysml#_graph_reflow_visible')
          \ )
  else
    call sysml#_graph_reflow_visible()
  endif
endfunction

function! sysml#_graph_reflow_visible(...) abort
  let s:graph_reflow_timer = -1
  for session_key in keys(copy(s:view_sessions))
    let buffer_number = str2nr(session_key)
    if get(s:view_sessions[session_key], 'method', '') ==# 'view_graph'
      call s:reflow_graph_buffer(buffer_number)
    endif
  endfor
endfunction

function! sysml#graph_mouse_sync(...) abort
  if get(b:, 'sysml_view_method', '') !=# 'view_graph'
        \ || get(b:, 'sysml_graph_syncing', 0)
    return
  endif

  if a:0 && a:1 ==# 'mouse'
    if !exists('*getmousepos')
      return
    endif
    " <MouseMove> does not move Vim's cursor, so resolve the pointer's actual window cell.
    let mouse = getmousepos()
    if get(mouse, 'winid', 0) != win_getid()
          \ || get(mouse, 'line', 0) < 1
          \ || get(mouse, 'column', 0) < 1
      return
    endif
    let current_line = mouse.line
    let current_column = virtcol([mouse.line, mouse.column])
  else
    let current_line = line('.')
    let current_column = virtcol('.')
  endif
  let layout = s:graph_layout()
  unlet! b:sysml_graph_selection
  call s:graph_highlight_selection()
  for node in layout.nodes
    if current_line >= node.top && current_line <= node.bottom
          \ && current_column >= node.left && current_column <= node.right
      let b:sysml_graph_selection = {
            \ 'kind': 'node',
            \ 'id': node.id,
            \ 'name': node.name
            \ }
      call s:graph_highlight_selection()
      call s:graph_set_cursor(node.line, node.col)
      return
    endif
  endfor

  let text = getline(current_line)
  if text =~# '^- '
    let edge_start = match(text, '- \zs\S')
    if edge_start >= 0
      for edge in layout.edges
        if edge.line == current_line
          let b:sysml_graph_selection = {
                \ 'kind': 'edge',
                \ 'id': get(edge, 'id', ''),
                \ 'source': edge.source,
                \ 'relation': edge.relation,
                \ 'target': edge.target
                \ }
          call s:graph_highlight_selection()
          call s:graph_set_cursor(current_line, edge.col)
          return
        endif
      endfor
      call s:graph_set_cursor(current_line, edge_start + 1)
      return
    endif
  endif

  for edge in layout.edges
    if s:edge_contains(edge, current_line, current_column)
      let b:sysml_graph_selection = {
            \ 'kind': 'edge',
            \ 'id': get(edge, 'id', ''),
            \ 'source': edge.source,
            \ 'relation': edge.relation,
            \ 'target': edge.target
            \ }
      call s:graph_highlight_selection()
      return
    endif
  endfor
endfunction

function! sysml#graph_inspect() abort
  if get(b:, 'sysml_view_method', '') !=# 'view_graph'
    echohl WarningMsg
    echom 'sysml graph inspection is only available in a graph view'
    echohl None
    return
  endif

  call sysml#graph_mouse_sync()
  let selection = get(b:, 'sysml_graph_selection', {})
  let layout = s:graph_layout()
  let inspection = []
  if get(selection, 'kind', '') ==# 'node'
    for node in layout.nodes
      if (!empty(get(selection, 'id', '')) && node.id ==# selection.id)
            \ || node.name ==# get(selection, 'name', '')
        let inspection = get(node, 'inspection', [])
        break
      endif
    endfor
  elseif get(selection, 'kind', '') ==# 'edge'
    for edge in layout.edges
      if (!empty(get(selection, 'id', '')) && edge.id ==# selection.id)
            \ || (edge.source ==# get(selection, 'source', '')
            \ && edge.relation ==# get(selection, 'relation', '')
            \ && edge.target ==# get(selection, 'target', ''))
        let inspection = get(edge, 'inspection', [])
        break
      endif
    endfor
  endif

  if type(inspection) != v:t_list || empty(inspection)
    echohl WarningMsg
    echom 'no projected inspection details for this graph element'
    echohl None
    return
  endif

  let source_buffer = bufnr('%')
  let source_window = win_getid()
  let inspection_name = 'sysml-inspect-' . source_buffer
  let inspection_buffer = bufnr(inspection_name)
  if inspection_buffer >= 0 && !empty(win_findbuf(inspection_buffer))
    call win_gotoid(win_findbuf(inspection_buffer)[0])
  elseif inspection_buffer >= 0
    tabnew
    execute 'buffer ' . inspection_buffer
  else
    tabnew
    execute 'file ' . fnameescape(inspection_name)
  endif
  setlocal buftype=nofile bufhidden=wipe nobuflisted noswapfile
  setlocal modifiable wrap linebreak
  call setline(1, inspection)
  if line('$') > len(inspection)
    execute (len(inspection) + 1) . ',$delete _'
  endif
  setlocal nomodified nomodifiable
  let b:sysml_inspection_source_buffer = source_buffer
  let b:sysml_inspection_source_window = source_window
  nnoremap <buffer> <silent> q :call sysml#graph_inspection_close()<CR>
  nnoremap <buffer> <silent> <Esc> :call sysml#graph_inspection_close()<CR>
endfunction

function! sysml#graph_inspection_close() abort
  let source_window = get(b:, 'sysml_inspection_source_window', -1)
  tabclose
  if source_window > 0 && win_gotoid(source_window) == 0
    echohl WarningMsg
    echom 'sysml inspection closed; the source graph window is no longer available'
    echohl None
  endif
endfunction

function! sysml#graph_move(direction) abort
  if get(b:, 'sysml_view_method', '') !=# 'view_graph'
    echohl WarningMsg
    echom 'sysml graph navigation is only available in a graph view'
    echohl None
    return
  endif
  if index(['left', 'right', 'up', 'down'], a:direction) < 0
    echohl ErrorMsg
    echom 'sysml graph movement expects left, right, up, or down'
    echohl None
    return
  endif

  let nodes = s:graph_layout().nodes
  if empty(nodes)
    echohl WarningMsg
    echom 'sysml graph has no nodes'
    echohl None
    return
  endif

  let current_node = {}
  for node in nodes
    if line('.') >= node.top && line('.') <= node.bottom
          \ && virtcol('.') >= node.left && virtcol('.') <= node.right
      let current_node = node
      break
    endif
  endfor
  if empty(current_node)
    let selection = get(b:, 'sysml_graph_selection', {})
    for node in nodes
      if (!empty(get(selection, 'id', '')) && node.id ==# selection.id)
            \ || (empty(get(selection, 'id', ''))
            \ && get(selection, 'kind', '') ==# 'node'
            \ && node.name ==# get(selection, 'name', ''))
        let current_node = node
        break
      endif
    endfor
  endif
  if empty(current_node)
    let cursor_line = line('.')
    let cursor_column = virtcol('.')
    let current_node = {
          \ 'id': '',
          \ 'top': cursor_line,
          \ 'bottom': cursor_line,
          \ 'left': cursor_column,
          \ 'right': cursor_column
          \ }
  endif

  let target = {}
  let horizontal = a:direction ==# 'left' || a:direction ==# 'right'
  let center = horizontal
        \ ? current_node.top + (current_node.bottom - current_node.top) / 2
        \ : current_node.left + (current_node.right - current_node.left) / 2
  let ray_extent = horizontal
        \ ? current_node.bottom - current_node.top
        \ : current_node.right - current_node.left
  let ray_offsets = [0]
  for offset in range(1, ray_extent)
    call add(ray_offsets, -offset)
    call add(ray_offsets, offset)
  endfor

  " Cast axis-aligned rays from the node's center, then from each row/column.
  for offset in ray_offsets
    let ray = center + offset
    let ray_target = {}
    let ray_distance = -1
    for node in nodes
      if node.id ==# current_node.id
        continue
      endif
      if horizontal
        if (a:direction ==# 'right' && node.left <= current_node.right)
              \ || (a:direction ==# 'left' && node.right >= current_node.left)
              \ || ray < node.top || ray > node.bottom
          continue
        endif
        let distance = a:direction ==# 'right'
              \ ? node.left - current_node.right
              \ : current_node.left - node.right
      else
        if (a:direction ==# 'down' && node.top <= current_node.bottom)
              \ || (a:direction ==# 'up' && node.bottom >= current_node.top)
              \ || ray < node.left || ray > node.right
          continue
        endif
        let distance = a:direction ==# 'down'
              \ ? node.top - current_node.bottom
              \ : current_node.top - node.bottom
      endif
      if ray_distance < 0 || distance < ray_distance
        let ray_distance = distance
        let ray_target = node
      endif
    endfor
    if !empty(ray_target)
      let target = ray_target
      break
    endif
  endfor

  if empty(target)
    let best_primary = -1
    let best_secondary = -1
    for node in nodes
      if node.id ==# current_node.id
        continue
      endif
      let x_gap = max([
            \ 0,
            \ node.left - current_node.right - 1,
            \ current_node.left - node.right - 1
            \ ])
      let y_gap = max([
            \ 0,
            \ node.top - current_node.bottom - 1,
            \ current_node.top - node.bottom - 1
            \ ])
      if (a:direction ==# 'left' && node.right >= current_node.left)
            \ || (a:direction ==# 'right' && node.left <= current_node.right)
            \ || (a:direction ==# 'up' && node.bottom >= current_node.top)
            \ || (a:direction ==# 'down' && node.top <= current_node.bottom)
        continue
      endif
      let primary = a:direction ==# 'left' || a:direction ==# 'right'
            \ ? x_gap : y_gap
      let secondary = a:direction ==# 'left' || a:direction ==# 'right'
            \ ? y_gap : x_gap
      if best_primary < 0 || primary < best_primary
            \ || (primary == best_primary && secondary < best_secondary)
        let best_primary = primary
        let best_secondary = secondary
        let target = node
      endif
    endfor
  endif

  if !empty(target)
    let b:sysml_graph_selection = {
          \ 'kind': 'node',
          \ 'id': target.id,
          \ 'name': target.name
          \ }
    call s:graph_highlight_selection()
    call s:graph_set_cursor(target.line, target.col)
  endif
endfunction

function! sysml#graph_navigate(kind, direction) abort
  if get(b:, 'sysml_view_method', '') !=# 'view_graph'
    echohl WarningMsg
    echom 'sysml graph navigation is only available in a graph view'
    echohl None
    return
  endif
  if index(['node', 'edge'], a:kind) < 0
    echohl ErrorMsg
    echom 'sysml graph navigation expects node or edge'
    echohl None
    return
  endif

  let positions = s:graph_positions(a:kind)
  if empty(positions)
    echohl WarningMsg
    echom 'sysml graph has no ' . a:kind . 's'
    echohl None
    return
  endif

  let current = [line('.'), col('.')]
  if a:direction > 0
    for position in positions
      if position[0] > current[0] || (position[0] == current[0] && position[1] > current[1])
        call cursor(position[0], position[1])
        return
      endif
    endfor
    let target = positions[0]
  else
    for position in reverse(copy(positions))
      if position[0] < current[0] || (position[0] == current[0] && position[1] < current[1])
        call cursor(position[0], position[1])
        return
      endif
    endfor
    let target = positions[-1]
  endif
  call cursor(target[0], target[1])
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
    call s:replace_buffer_lines(
          \ result_buffer,
          \ refreshed_view.lines,
          \ get(refreshed_view, 'layout', {})
          \ )
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
  let document_state = s:workspace_documents(path, bufnr('%'))
  let params = {'path': path}
  if !empty(document_state.documents)
    let params.documents = document_state.documents
  endif
  let rpc = s:rpc_request('check', params)
  if get(rpc, 'ok', v:false)
    call sysml#_handle_check(0, [json_encode(rpc.result)])
    return
  endif

  if document_state.has_modified_buffers
    echohl ErrorMsg
    echom 'sysml check failed; unsaved SysML text requires a working RPC backend: '
          \ . get(get(rpc, 'error', {}), 'message', 'RPC request failed')
    echohl None
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

function! sysml#command(...) abort
  if a:0 == 0
    return sysml#help()
  endif

  let commands = {
        \ 'help': ['sysml#help', 0],
        \ 'check': ['sysml#check', 1],
        \ 'check-workspace': ['sysml#check_workspace', 1],
        \ 'tree': ['sysml#tree', 1],
        \ 'view': ['sysml#view', 2],
        \ 'graph': ['sysml#graph', 1],
        \ 'find': ['sysml#find', 2],
        \ 'definition': ['sysml#definition', 1],
        \ 'references': ['sysml#references', 1],
        \ 'hover': ['sysml#hover', 1],
        \ 'relationships': ['sysml#relationships', 1],
        \ 'requirements': ['sysml#requirements', 1],
        \ 'traceability': ['sysml#traceability', 1],
        \ 'health': ['sysml#health', 0],
        \ 'log': ['sysml#log', 0],
        \ 'restart': ['sysml#restart', 0]
        \ }
  let subcommand = tolower(a:1)
  if !has_key(commands, subcommand)
    echoerr 'sysml-vim: unknown command: ' . a:1
    return -1
  endif
  let command = commands[subcommand]
  let args = a:000[1:]
  if len(args) > command[1]
    echoerr printf('sysml-vim: %s accepts at most %d argument(s)', subcommand, command[1])
    return -1
  endif
  return call(command[0], args)
endfunction

function! sysml#help() abort
  help sysml-vim
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
  let graph_width = max([40, winwidth(0)])
  let params.width = graph_width
  if !empty(focus)
    let params.focus = focus
  endif
  let args = [
        \ 'view', 'composition', '--path', context.path,
        \ '--format', 'graph-json', '--depth', '5',
        \ '--width', string(graph_width)
        \ ]
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
