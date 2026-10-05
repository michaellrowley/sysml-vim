local M = {}

local function sibling_command(command, sibling)
  local command_path = command:find("[/\\]") and command or vim.fn.exepath(command)
  if command_path == "" then
    return sibling
  end
  local suffix = (vim.fn.has("win32") == 1 or vim.fn.has("win64") == 1) and ".exe" or ""
  return vim.fn.fnamemodify(command_path, ":h") .. "/" .. sibling .. suffix
end

function M.setup(opts)
  opts = opts or {}
  if opts.backend_cmd then
    vim.g.sysml_backend_cmd = opts.backend_cmd
    if not opts.rpc_cmd then
      vim.g.sysml_rpc_cmd = sibling_command(opts.backend_cmd, "sysml-rpc")
    end
  end
  if opts.rpc_cmd then
    vim.g.sysml_rpc_cmd = opts.rpc_cmd
    if not opts.backend_cmd then
      vim.g.sysml_backend_cmd = sibling_command(opts.rpc_cmd, "sysml")
    end
  end
  if opts.default_view then
    vim.g.sysml_default_view = opts.default_view
  end
end

return M
