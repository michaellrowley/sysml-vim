# Configuration

## Vim globals

- `g:sysml_backend_cmd` (default: `sysml`)
- `g:sysml_default_view` (default: `composition`)
- `g:sysml_use_rpc` (default: `1`) enables persistent `sysml-rpc` usage with CLI fallback
- `g:sysml_rpc_cmd` (default: `sysml-rpc`)
- `g:sysml_rpc_timeout_ms` (default: `4000`)

## Environment variables

- `SYSML_PILOT_COMMAND`: argv adapter mode (`<cmd> <operation> <workspace>`, JSON payload on stdin)
- `SYSML_PILOT_RPC_COMMAND`: JSON-RPC adapter mode (line-delimited JSON-RPC over stdio)

## Health report

Run `:SysmlHealth` or `sysml health --path .`.
