if exists('b:current_syntax')
  finish
endif

syntax keyword sysmlKeyword package import part port interface connection item action state requirement satisfy verify allocate specialize redefines
syntax keyword sysmlDefKeyword def
syntax match sysmlType /\<[A-Z][A-Za-z0-9_]*\>/
syntax match sysmlComment "//.*$"
syntax region sysmlString start=/"/ skip=/\\"/ end=/"/

highlight default link sysmlKeyword Keyword
highlight default link sysmlDefKeyword Statement
highlight default link sysmlType Type
highlight default link sysmlComment Comment
highlight default link sysmlString String

let b:current_syntax = 'sysml'
