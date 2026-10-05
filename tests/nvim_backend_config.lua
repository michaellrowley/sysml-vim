require("sysml").setup({
  backend_cmd = "/matching/venv/bin/sysml",
})

assert(vim.g.sysml_backend_cmd == "/matching/venv/bin/sysml")
assert(vim.g.sysml_rpc_cmd == "/matching/venv/bin/sysml-rpc")

require("sysml").setup({
  rpc_cmd = "/another/venv/bin/sysml-rpc",
})

assert(vim.g.sysml_backend_cmd == "/another/venv/bin/sysml")
assert(vim.g.sysml_rpc_cmd == "/another/venv/bin/sysml-rpc")

require("sysml").setup({
  backend_cmd = "/matching/venv/bin/sysml",
  rpc_cmd = "/matching/venv/bin/sysml-rpc",
})

assert(vim.g.sysml_backend_cmd == "/matching/venv/bin/sysml")
assert(vim.g.sysml_rpc_cmd == "/matching/venv/bin/sysml-rpc")
