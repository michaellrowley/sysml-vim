# API / Protocol

`sysml-rpc` implements line-delimited JSON-RPC 2.0 over stdio.

Methods:

- `check`, `symbols`, `definition`, `references`, `hover`, `completion`, `query`, `tree`, `view`, `health`, `shutdown`

Each method accepts `params.path` and method-specific keys.
