setlocal commentstring=//\ %s
setlocal omnifunc=sysml#complete
setlocal foldmethod=expr
setlocal foldexpr=getline(v:lnum)=~'{'?'>1':getline(v:lnum)=~'}'?'<1':'='
