# API / Protocol

`sysml-rpc` implements line-delimited JSON-RPC 2.0 over stdio.

Methods:

- `check`, `symbols`, `definition`, `references`, `hover`, `completion`, `query`, `tree`, `view`, `view_text`, `view_graph`, `health`, `parser_status`, `shutdown`

Each method accepts `params.path` and method-specific keys. View methods also accept an optional `params.documents` list of `{ "path": "...", "text": "..." }` objects. These in-memory document overrides are scoped to the workspace, participate in the parser index, and do not write files to disk.

Model operations use the configured SysML language server. RPC requests reuse the indexed model while the workspace's file paths, modification times, sizes, and document overrides are unchanged; set `params.refresh` to `true` to force a new parse. The server remains alive for the RPC service lifetime and reuses its parse cache. `health` and `parser_status` report configuration without starting the language server.
