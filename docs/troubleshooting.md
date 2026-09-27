# Troubleshooting

- `sysml: command not found`: install backend (`pip install -e .`) and set `g:sysml_backend_cmd`.
- No SVG output: install Graphviz (`dot`) and re-run `sysml health`.
- `SysML v2 parsing is unavailable`: build the official Pilot checkout with Java 21 and `./mvnw clean install`, then set `SYSML_PILOT_HOME` and `SYSML_PILOT_COMMAND` as shown in [the setup guide](pilot-parser.md).
- Bridge cannot find parser JAR: check that `SYSML_PILOT_HOME/org.omg.sysml.interactive/target/` contains exactly one `org.omg.sysml.interactive-*-all.jar`, or set `SYSML_PILOT_JAR` directly.
- `javac` or Java class-version error: install a Java 21 JDK and ensure both `java` and `javac` resolve to it on `PATH`.
- Parser response rejected: check the bridge's stdout contains only the JSON response and that its parser metadata, file paths, source ranges, diagnostics, and standards list match [the contract](pilot-parser.md).
- Missing diagnostics/references: confirm the configured bridge delegates to the official Pilot parser and validator and passes through its diagnostics; sysml-vim does not independently validate unresolved names.
