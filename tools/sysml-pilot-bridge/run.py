#!/usr/bin/env python3
"""Compile and run the sysml-vim bridge against the official Pilot fat JAR."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


BRIDGE_SOURCE = Path(__file__).parent / "src" / "org" / "sysmlvim" / "bridge" / "PilotBridge.java"
PILOT_JAR_NAME = "org.omg.sysml.interactive-*-all.jar"


def fail(message: str) -> int:
    print(f"sysml-pilot-bridge: {message}", file=sys.stderr)
    return 2


def resolve_pilot_jar() -> Path:
    configured_jar = os.environ.get("SYSML_PILOT_JAR")
    if configured_jar:
        pilot_jar = Path(configured_jar).expanduser().resolve()
        if not pilot_jar.is_file():
            raise FileNotFoundError(f"SYSML_PILOT_JAR does not exist: {pilot_jar}")
        return pilot_jar

    pilot_home = os.environ.get("SYSML_PILOT_HOME")
    if not pilot_home:
        raise FileNotFoundError(
            "Set SYSML_PILOT_HOME to a built SysML-v2-Pilot-Implementation checkout "
            "or SYSML_PILOT_JAR to its interactive *-all.jar"
        )

    jar_directory = Path(pilot_home).expanduser() / "org.omg.sysml.interactive" / "target"
    matching_jars = sorted(jar_directory.glob(PILOT_JAR_NAME))
    if len(matching_jars) != 1:
        raise FileNotFoundError(
            f"Expected one {PILOT_JAR_NAME} in {jar_directory}; build the Pilot checkout first"
        )
    return matching_jars[0].resolve()


def build_directory_for(pilot_jar: Path) -> Path:
    cache_root = (
        os.environ.get("XDG_CACHE_HOME")
        or os.environ.get("LOCALAPPDATA")
        or str(Path.home() / ".cache")
    )
    return Path(cache_root) / "sysml-vim" / "pilot-bridge" / pilot_jar.name


def compile_bridge(pilot_jar: Path, build_directory: Path) -> int:
    java_compiler = shutil.which("javac")
    if java_compiler is None:
        return fail("javac was not found; install a Java 21 JDK and add it to PATH")

    compiled_class = build_directory / "org" / "sysmlvim" / "bridge" / "PilotBridge.class"
    build_marker = build_directory / ".compiled"
    if (
        compiled_class.is_file()
        and build_marker.is_file()
        and compiled_class.stat().st_mtime_ns >= BRIDGE_SOURCE.stat().st_mtime_ns
        and compiled_class.stat().st_mtime_ns >= pilot_jar.stat().st_mtime_ns
    ):
        return 0

    build_directory.mkdir(parents=True, exist_ok=True)
    compilation = subprocess.run(
        [
            java_compiler,
            "-encoding",
            "UTF-8",
            "-cp",
            str(pilot_jar),
            "-d",
            str(build_directory),
            str(BRIDGE_SOURCE),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if compilation.returncode:
        if compilation.stderr:
            print(compilation.stderr, file=sys.stderr, end="")
        return compilation.returncode
    build_marker.touch()
    return 0


def main() -> int:
    try:
        pilot_jar = resolve_pilot_jar()
    except FileNotFoundError as error:
        return fail(str(error))

    java_runtime = shutil.which("java")
    if java_runtime is None:
        return fail("java was not found; install a Java 21 JDK and add it to PATH")

    build_directory = build_directory_for(pilot_jar)
    compile_status = compile_bridge(pilot_jar, build_directory)
    if compile_status:
        return compile_status

    environment = os.environ.copy()
    pilot_version = pilot_jar.name.removeprefix("org.omg.sysml.interactive-").removesuffix("-all.jar")
    environment.setdefault("SYSML_PILOT_VERSION", pilot_version)
    pilot_home = environment.get("SYSML_PILOT_HOME")
    if not environment.get("SYSML_PILOT_LIBRARY") and pilot_home:
        candidate_library = Path(pilot_home) / "sysml.library"
        if candidate_library.is_dir():
            environment["SYSML_PILOT_LIBRARY"] = str(candidate_library.resolve())

    try:
        os.execve(
            java_runtime,
            [
                java_runtime,
                "-cp",
                os.pathsep.join((str(build_directory), str(pilot_jar))),
                "org.sysmlvim.bridge.PilotBridge",
                *sys.argv[1:],
            ],
            environment,
        )
    except OSError as error:
        return fail(f"could not start the Pilot bridge: {error}")


if __name__ == "__main__":
    raise SystemExit(main())
