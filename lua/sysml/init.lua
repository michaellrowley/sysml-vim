local M = {}

function M.setup(opts)
  opts = opts or {}
  if opts.backend_cmd then
    vim.g.sysml_backend_cmd = opts.backend_cmd
  end
  if opts.default_view then
    vim.g.sysml_default_view = opts.default_view
  end
end

return M
