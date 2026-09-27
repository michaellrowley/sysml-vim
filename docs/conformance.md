# Conformance and compatibility

## Targeted standards context

- OMG KerML 1.0, SysML 2.0, Systems Modeling API/Services 1.0 (formally adopted; release docs updated 2026-08)
- Upstream refs used:
  - SysML-v2-Release `fb97b754f29588b8e9c7a35f370880cd15eb29e7`
  - SysML-v2-Pilot-Implementation `5cca16d846016e62bb1e54e0e50e675254a022ef` (0.63.0)

## What this release implements

- Useful offline structural parsing/indexing for `.sysml`/`.kerml`
- Cross-file symbol/reference workflows, diagnostics, hover, completion
- Semantic query and view projections with text/dot/svg outputs
- Vim/Neovim workflows backed by the CLI/backend

## What this release does not claim

- Full grammar-derived parse and complete SysML/KerML semantic conformance
- Complete Systems Modeling API workflow implementation
- Full official graphical notation conformance

## Official tooling integration status

- Implemented adapter boundary for external pilot tooling (`SYSML_PILOT_COMMAND`)
- In this repository, official pilot implementation is **not bundled**
- Capability reporting is explicit via `sysml health`
