# Architecture

- Editor front-end (Vimscript): commands, mappings, quickfix, buffers
- Backend service (Python): delegates parsing and standards validation to the configured Pilot bridge, then indexes its diagnostics and model projections for queries and views
- CLI (`sysml`) and JSON-RPC (`sysml-rpc`) are editor-independent interfaces
- Rendering layer: text, DOT, SVG
- Parser bridge: `OfficialPilotAdapter` invokes the included Java adapter over `SYSML_PILOT_COMMAND` or `SYSML_PILOT_RPC_COMMAND`. The launcher compiles against the official Pilot fat JAR and initializes its SysML/KerML Xtext setups; no local parser or fallback exists
- Index and view projections cover selected symbols and relationships, not the complete SysML/KerML semantic model

The Pilot checkout and Java 21 build remain external prerequisites. The included bridge contract and setup are documented in [pilot-parser.md](pilot-parser.md); this keeps editor logic thin and makes the parser's version and limits explicit.
