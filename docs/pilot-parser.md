# Official SysML v2 parser bridge

The repository includes a Java bridge that uses the [SysML v2 Pilot Implementation](https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation)'s Xtext resource factories, model library, and `IResourceValidator`. It initializes the Pilot's own SysML/KerML standalone setups, loads all workspace resources into one Pilot resource set, resolves cross-file references, and returns Pilot diagnostics with selected model projections. No SysML grammar or local validation rules are implemented here.

## Prerequisites

Install a Java 21 JDK (`java` and `javac` on `PATH`) and build the official Pilot checkout. Its Maven wrapper downloads Maven and the required dependencies:

On macOS with Homebrew, the [full installer](installation.md#automated-full-install-on-macos) can install missing prerequisites, build the Pilot, install the Vim plugin, and configure its Python environment in one run. From an existing sysml-vim checkout, run `./tools/install.sh`.

```sh
git clone https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation.git
cd SysML-v2-Pilot-Implementation
./mvnw clean install
```

The command-line build does not require launching the Eclipse IDE. It builds the Pilot plugins and its shaded parser JAR at `org.omg.sysml.interactive/target/org.omg.sysml.interactive-*-all.jar`; the model libraries are in `sysml.library/`.

From the sysml-vim checkout, install the Python package and configure the installed bridge command:

```sh
python3 -m pip install -e .
export SYSML_PILOT_HOME="$HOME/SysML-v2-Pilot-Implementation"
export SYSML_PILOT_COMMAND="sysml-pilot-bridge"
sysml health
sysml check tests/fixtures/workspace
```

Run the install command from the sysml-vim checkout. It installs the `sysml-pilot-bridge` console command and packages the Java bridge source, so the parser command needs no absolute path to the checkout. Activate the Python environment used for installation or add its `bin`/`Scripts` directory to `PATH`, including in the environment that launches Vim/Neovim. The bridge finds the shaded JAR and model libraries under `SYSML_PILOT_HOME`; on first use it compiles `PilotBridge.java` with `javac`, caches the class files outside the repository (`$XDG_CACHE_HOME` or `~/.cache`), then starts the Pilot parser. Set `SYSML_PILOT_JAR` or `SYSML_PILOT_LIBRARY` only if those resources are not in their normal checkout locations. For JSON-RPC transport, set `SYSML_PILOT_RPC_COMMAND=sysml-pilot-bridge` instead; it accepts both transports.

The editor inherits environment variables from the process that starts it. For GUI Vim/Neovim, configure the variables in the GUI launch environment as well as in shell startup files.

## Request and response

In argv mode, the backend starts the configured command with `parse <workspace-path>`, writes one JSON request to stdin, and reads one JSON response from stdout. The request contains every `.sysml` and `.kerml` source in the workspace:

```json
{
  "files": [
    {"path": "/workspace/model.sysml", "text": "package Example { part def Vehicle; }"}
  ]
}
```

In RPC mode, the backend sends a single JSON-RPC 2.0 request with method `parse` and parameters containing `path` (the workspace root) and `files` (the same array). The response's `result` is the JSON object below.

```json
{
  "parser": {
    "name": "SysML v2 Pilot Implementation",
    "version": "0.63.0",
    "standards": ["SysML 2.0", "KerML 1.0"]
  },
  "files": [
    {
      "path": "/workspace/model.sysml",
      "symbols": [
        {
          "name": "Vehicle",
          "kind": "part_def",
          "range": {"line": 1, "col": 31, "end_col": 38},
          "container": "Example",
          "signature": "part def Vehicle;"
        }
      ],
      "references": [],
      "diagnostics": [],
      "imports": []
    }
  ]
}
```

Each requested source path must occur exactly once in `files`. The bridge must return source locations using 1-based lines and 0-based columns. Symbols and references are projections for navigation and views; validation diagnostics must come from the Pilot, not a second local check. A diagnostic contains `range`, `severity` (`error`, `warning`, or `info`), and `message`; `source` is optional. A symbol has `name`, `kind`, and `range`, with optional `container` and `signature`. A reference has `name` and `range`, with optional `relation` and `source`. The `imports` array contains the file's imported qualified names.

Nonzero bridge exits, malformed JSON, missing metadata/files, unsupported standards metadata, and invalid ranges are surfaced as backend errors. Health reports bridge configuration without launching Java; `sysml check` is the end-to-end parser check. There is no subset-parser fallback.

## Limits

The Pilot is an evolving implementation, not a guarantee of complete conformance to every normative SysML/KerML rule. The bridge reports the built Pilot artifact version in `parser.version`; assess its conformance separately. The sysml-vim index and view layer intentionally project selected symbols and relationships; they are not a complete semantic model API client. The bridge source is included, but the official Pilot's separately licensed/plugin-based checkout and build are prerequisites.
