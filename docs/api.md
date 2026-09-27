# API / Protocol

`sysml-rpc` implements line-delimited JSON-RPC 2.0 over stdio.

Methods:

- `check`, `symbols`, `definition`, `references`, `hover`, `completion`, `query`, `tree`, `view`, `view_text`, `view_graph`, `health`, `official`, `official_status`, `shutdown`

Each method accepts `params.path` and method-specific keys.

Model operations parse files through the configured Pilot bridge. RPC requests reuse the indexed model while the workspace's file paths, modification times, and sizes are unchanged; set `params.refresh` to `true` to force a new parse. `health` and `official_status` report bridge configuration without starting a parser process.
