# Configuration

## Vim globals

- `g:sysml_backend_cmd` (default: `sysml`)
- `g:sysml_default_view` (default: `composition`)
- `g:sysml_use_rpc` (default: `1`) enables persistent `sysml-rpc` usage with CLI fallback
- `g:sysml_rpc_cmd` (default: `sysml-rpc`)
- `g:sysml_rpc_timeout_ms` (default: `120000`; allow the Pilot time to start and validate a workspace)

## Environment variables

- `SYSML_PILOT_HOME`: official Pilot checkout built with `./mvnw clean install`; the included launcher locates its parser JAR and model libraries here
- `SYSML_PILOT_COMMAND`: included launcher in argv mode; set to `python3 /path/to/sysml-vim/tools/sysml-pilot-bridge/run.py`
- `SYSML_PILOT_RPC_COMMAND`: optional JSON-RPC transport using the same launcher (takes precedence when both command variables are set)
- `SYSML_PILOT_JAR`: optional explicit path to the Pilot's `org.omg.sysml.interactive-*-all.jar`
- `SYSML_PILOT_LIBRARY`: optional explicit path to the Pilot's `sysml.library` directory

The included launcher compiles its Java bridge against the official Pilot JAR on first use and caches the class files outside the repository. See [the complete build and installation instructions](pilot-parser.md). No built-in subset parser or fallback is available.

## Health report

Run `:SysmlHealth` or `sysml health --path .` to confirm bridge configuration. Health does not start Java; run `sysml check` to confirm the Pilot JAR can be loaded and the workspace validates.
