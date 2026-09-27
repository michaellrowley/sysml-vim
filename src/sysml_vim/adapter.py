from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
from typing import Any


class OfficialPilotAdapter:
    """Optional adapter boundary for external official SysML v2 tooling."""

    def __init__(self) -> None:
        self.command = os.getenv("SYSML_PILOT_COMMAND")

    def available(self) -> bool:
        return bool(self.command)

    def invoke(self, operation: str, workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.command:
            return {
                "ok": False,
                "error": "SYSML_PILOT_COMMAND is not configured",
                "operation": operation,
                "capability": "local-fallback-only",
            }

        argv = shlex.split(self.command)
        if not argv:
            return {
                "ok": False,
                "error": "SYSML_PILOT_COMMAND is empty after parsing",
                "operation": operation,
            }

        proc = subprocess.run(
            [*argv, operation, str(workspace)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            return {
                "ok": False,
                "error": proc.stderr.strip() or f"command exited with code {proc.returncode}",
                "operation": operation,
                "capability": "adapter-error",
            }
        try:
            result = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            return {
                "ok": False,
                "error": "adapter returned non-JSON output",
                "stdout": proc.stdout[-500:],
                "operation": operation,
            }
        return {"ok": True, "result": result}
