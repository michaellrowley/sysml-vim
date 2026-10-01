# Architecture

- Editor front-end (Vimscript): commands, mappings, quickfix, buffers
- Backend service (Python): delegates parsing and diagnostics to the SysML v2 language server, then indexes its diagnostics and model projections for queries and views
- CLI (`sysml`) and JSON-RPC (`sysml-rpc`) are editor-independent interfaces
- Rendering layer: text, DOT, SVG, and structured terminal/editor graph layouts; focused SysML view usages can select standard view presentations from their projected view-definition typing
- Parser adapter: `SysMLLspAdapter` keeps one standard LSP stdio process per workspace, requests the LSP project's `sysml/model` projection, document symbols, diagnostics, and references, then maps them into the backend's stable index format
- Index and view projections cover selected symbols and relationships, not the complete SysML/KerML semantic model

The parser is the third-party `sysml-v2-lsp` package, which uses generated ANTLR code from an OMG KEBNF-derived grammar. Node.js 20+ is required. The persistent RPC service reuses the LSP process and its document cache; graph layout and rendering remain in Python. This integration is not a claim of Pilot-equivalent or complete standards validation; see [the setup and limits](lsp-parser.md).
