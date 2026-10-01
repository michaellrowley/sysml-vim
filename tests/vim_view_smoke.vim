set nocompatible
let s:repository_root = getcwd()
execute 'set runtimepath^=' . fnameescape(s:repository_root)
filetype plugin on
source plugin/sysml.vim

let $PYTHONPATH = s:repository_root . '/src' . (empty($PYTHONPATH) ? '' : ':' . $PYTHONPATH)
let $SYSML_LSP_COMMAND = 'python3 ' . shellescape(s:repository_root . '/tests/fixtures/mock_lsp_server.py')
let $SYSML_LSP_SERVER = ''
let g:sysml_rpc_cmd = exepath('sysml-rpc')
let g:sysml_rpc_timeout_ms = 10000
let g:sysml_view_refresh_delay_ms = 100
let s:workspace = s:repository_root . '/tests/fixtures/workspace'
let s:source_file = s:workspace . '/vehicle.sysml'

execute 'edit ' . fnameescape(s:source_file)
execute 'lcd ' . fnameescape(s:workspace)
if &filetype !=# 'sysml'
  setfiletype sysml
endif
if &l:foldlevel != 99 || foldclosed(2) != -1
  cquit 1
endif

let s:source_buffer = bufnr('%')
call append(line('$') - 1, '  part def DraftOnly;')
call feedkeys(":v2t\<CR>", 'xt')
let s:tree_buffer = bufnr('%')
if bufname('%') !~# '^sysml-tree-' || winnr('$') != 1
  cquit 2
endif
if join(getline(1, '$'), "\n") !~# 'DraftOnly'
  cquit 3
endif
if tabpagenr('$') != 2
  cquit 4
endif

tabprevious
if bufnr('%') != s:source_buffer
  cquit 5
endif
call append(line('$') - 1, '  part def LiveUpdate;')
doautocmd TextChanged
sleep 500m
if join(getbufline(s:tree_buffer, 1, '$'), "\n") !~# 'LiveUpdate'
  cquit 6
endif

call sysml#graph('DraftOnly')
if bufname('%') !~# '^sysml-graph-' || winnr('$') != 1
  cquit 7
endif
if join(getline(1, '$'), "\n") !~# 'DraftOnly'
  cquit 8
endif

tabfirst
call cursor(1, 1)
call sysml#graph()
let s:graph_buffer = bufnr('%')
let s:edge_header_line = search('^Edges:$', 'n')
if join(getline(1, '$'), "\n") !~# 'Vehicle'
  cquit 11
endif
let s:selection_match_id = get(w:, 'sysml_graph_selection_match', -1)
let s:selection_match = {}
let s:has_node_color = 0
let s:has_edge_color = 0
let s:has_edge_route_color = 0
for s:match in getmatches()
  if s:match.id == s:selection_match_id
    let s:selection_match = s:match
  endif
  if s:match.group ==# 'SysmlGraphNodeStructure'
    let s:has_node_color = 1
  elseif s:match.group ==# 'SysmlGraphEdgeRoute'
    let s:has_edge_route_color = 1
    for s:match_index in range(1, 8)
      let s:position = get(s:match, 'pos' . s:match_index, [])
      if !empty(s:position) && s:position[0] < s:edge_header_line
        let s:has_edge_route_color = 2
      endif
    endfor
  elseif s:match.group ==# 'SysmlGraphEdgeTyping'
    let s:has_edge_color = 1
  endif
endfor
let s:selected_node = {}
for s:node in get(get(b:, 'sysml_graph_layout', {}), 'nodes', [])
  if s:node.name ==# get(get(b:, 'sysml_graph_selection', {}), 'name', '')
    let s:selected_node = s:node
    break
  endif
endfor
if &l:cursorline || empty(s:selection_match) || empty(s:selected_node)
      \ || !s:has_node_color || !s:has_edge_color
      \ || s:has_edge_route_color != 2 || !hlexists('SysmlGraphJunction')
  cquit 24
endif
if &l:wrap || &l:sidescroll != 1
  cquit 27
endif
if get(s:selection_match, 'group', '') !=# 'SysmlGraphSelection'
  cquit 26
endif
let s:top_box_text = strcharpart(
      \ getline(s:selected_node.top),
      \ s:selected_node.left - 1,
      \ s:selected_node.right - s:selected_node.left + 1
      \ )
let s:top_box_byte_column = strlen(strcharpart(
      \ getline(s:selected_node.top),
      \ 0,
      \ s:selected_node.left - 1
      \ )) + 1
if get(s:selection_match, 'pos1', []) !=# [
      \ s:selected_node.top,
      \ s:top_box_byte_column,
      \ strlen(s:top_box_text)
      \ ]
  cquit 25
endif
if empty(maparg(']n', 'n')) || empty(maparg('[n', 'n'))
      \ || empty(maparg(']e', 'n')) || empty(maparg('[e', 'n'))
      \ || empty(maparg('<Left>', 'n')) || empty(maparg('<Right>', 'n'))
      \ || empty(maparg('<Up>', 'n')) || empty(maparg('<Down>', 'n'))
  cquit 14
endif
call cursor(1, 1)
normal ]n
if getline('.') !~# '│.*│'
  cquit 15
endif
let s:first_node_position = [line('.'), col('.')]
normal ]n
if [line('.'), col('.')] ==# s:first_node_position
  cquit 18
endif
normal ]e
if getline('.') !~# '^- '
  cquit 16
endif
normal [n
if getline('.') !~# '│.*│'
  cquit 17
endif
let s:selected_node_position = [line('.'), col('.')]
call cursor(line('.'), col('.') + 1)
call sysml#graph_mouse_sync()
if [line('.'), col('.')] !=# s:selected_node_position
  cquit 19
endif
normal ]e
let s:selected_edge_position = [line('.'), col('.')]
call cursor(line('.'), col('.') + 1)
call sysml#graph_mouse_sync()
if [line('.'), col('.')] !=# s:selected_edge_position
  cquit 20
endif
let s:edge_route_selected = 0
for s:graph_line in range(3, s:edge_header_line - 1)
  let s:arrow_column = match(getline(s:graph_line), '▶')
  if s:arrow_column >= 0
    call cursor(s:graph_line, s:arrow_column + 1)
    let s:edge_route_position = [line('.'), col('.')]
    call sysml#graph_mouse_sync()
    if [line('.'), col('.')] ==# s:edge_route_position
          \ && get(get(b:, 'sysml_graph_selection', {}), 'kind', '') ==# 'edge'
      let s:edge_route_selected = 1
      break
    endif
  endif
endfor
if !s:edge_route_selected
  cquit 23
endif
call cursor(1, 1)
normal ]n
let s:node_before_arrow = [line('.'), col('.')]
execute "normal \<Right>"
if [line('.'), col('.')] ==# s:node_before_arrow
  cquit 21
endif
if getline('.') !~# '│.*│'
  cquit 22
endif

let s:navigation_nodes = get(get(b:, 'sysml_graph_layout', {}), 'nodes', [])
let s:leftmost_node = {}
let s:max_node_right = 0
for s:node in s:navigation_nodes
  let s:center_x = s:node.left + (s:node.right - s:node.left) / 2
  if empty(s:leftmost_node)
        \ || s:center_x < s:leftmost_node.left
              \ + (s:leftmost_node.right - s:leftmost_node.left) / 2
    let s:leftmost_node = s:node
  endif
  let s:max_node_right = max([s:max_node_right, s:node.right])
endfor
let b:sysml_graph_selection = {
      \ 'kind': 'node',
      \ 'id': s:leftmost_node.id,
      \ 'name': s:leftmost_node.name
      \ }
call cursor(s:leftmost_node.line, s:leftmost_node.col)
if virtcol('.') < s:leftmost_node.left || virtcol('.') > s:leftmost_node.right
  cquit 28
endif
let s:current_node = s:leftmost_node
let s:navigation_steps = 0
while s:navigation_steps < len(s:navigation_nodes)
  call sysml#graph_move('right')
  let s:selection_id = get(get(b:, 'sysml_graph_selection', {}), 'id', '')
  if s:selection_id ==# s:current_node.id
    break
  endif
  let s:next_node = {}
  for s:node in s:navigation_nodes
    if s:node.id ==# s:selection_id
      let s:next_node = s:node
      break
    endif
  endfor
  if empty(s:next_node)
    cquit 29
  endif
  if s:next_node.left + (s:next_node.right - s:next_node.left) / 2
        \ <= s:current_node.left
              \ + (s:current_node.right - s:current_node.left) / 2
    cquit 30
  endif
  let s:current_node = s:next_node
  let s:navigation_steps += 1
endwhile
if s:current_node.right != s:max_node_right
  cquit 31
endif

let s:workspace_b = tempname()
call mkdir(s:workspace_b, 'p')
let s:second_source_file = s:workspace_b . '/links.sysml'
call writefile(
      \ readfile(s:repository_root . '/tests/fixtures/workspace/links.sysml', 'b'),
      \ s:second_source_file,
      \ 'b'
      \ )
execute 'tabnew ' . fnameescape(s:second_source_file)
execute 'lcd ' . fnameescape(s:workspace_b)
let s:second_source_buffer = bufnr('%')
call append(line('$') - 1, '  part def DraftFromWorkspaceB;')
call sysml#tree()
let s:second_tree_buffer = bufnr('%')
if bufname('%') !=# 'sysml-tree-' . s:second_source_buffer || winnr('$') != 1
  cquit 9
endif
if tabpagenr('$') != 5
  cquit 10
endif

call win_gotoid(win_findbuf(s:source_buffer)[0])
call append(line('$') - 1, '  part def UpdateFromWorkspaceA;')
doautocmd TextChanged
sleep 20m

call win_gotoid(win_findbuf(s:second_source_buffer)[0])
call append(line('$') - 1, '  part def UpdateFromWorkspaceB;')
doautocmd TextChanged
sleep 500m

if join(getbufline(s:tree_buffer, 1, '$'), "\n") !~# 'UpdateFromWorkspaceA'
  cquit 12
endif
if join(getbufline(s:second_tree_buffer, 1, '$'), "\n") !~# 'UpdateFromWorkspaceB'
  cquit 13
endif
let s:refreshed_graph_layout = getbufvar(s:graph_buffer, 'sysml_graph_layout', {})
if empty(filter(
      \ copy(get(s:refreshed_graph_layout, 'nodes', [])),
      \ 'v:val.name ==# "UpdateFromWorkspaceA"'
      \ ))
  cquit 27
endif
let s:graph_window = win_findbuf(s:graph_buffer)[0]
call win_execute(
      \ s:graph_window,
      \ 'let b:sysml_graph_test_matches = getmatches()')
let s:graph_test_matches = getbufvar(s:graph_buffer, 'sysml_graph_test_matches', [])
if empty(filter(
      \ copy(s:graph_test_matches),
      \ 'v:val.group ==# "SysmlGraphNodeStructure"'))
  cquit 28
endif

call delete(s:workspace_b, 'rf')
quitall!
