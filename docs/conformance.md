# Conformance and compatibility

## Targeted standards context

- OMG KerML 1.0, SysML 2.0, Systems Modeling API/Services 1.0 (formally adopted; release docs updated 2026-08)
- Upstream refs used:
  - SysML-v2-Release `fb97b754f29588b8e9c7a35f370880cd15eb29e7`
  - SysML-v2-Pilot-Implementation `5cca16d846016e62bb1e54e0e50e675254a022ef` (0.63.0)

## Parser integration

- Official Pilot grammar-based parser and validator bridge for `.sysml` and `.kerml`; actual coverage follows the configured Pilot version
- Cross-file symbol/reference workflows, Pilot diagnostics, hover, and completion from bridge-produced model projections
- Semantic query and view projections with text/dot/svg outputs
- Vim/Neovim workflows backed by the parser-dependent CLI/backend
- Fixtures covering composition, requirements, imports/allocation/trace, and state transitions

## Scope and limitations

- Complete conformance to every normative SysML/KerML validation rule is not guaranteed by the evolving Pilot implementation
- Complete Systems Modeling API workflow implementation
- Full official graphical notation conformance
- Zero-configuration parser setup: the bridge source is included, but the official Pilot and Java 21 are separate prerequisites that must be installed and built
- A complete model semantic API: indexing and views expose selected bridge-provided projections only
- Any local parsing or validation fallback when the Pilot bridge is missing or fails
