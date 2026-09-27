from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
from typing import Any


class OfficialPilotAdapter:
    """Adapter boundary for external official SysML v2 tooling.

    Supported modes:
    1) argv mode via SYSML_PILOT_COMMAND (command receives: <operation> <workspace>, JSON payload on stdin)
    2) rpc mode via SYSML_PILOT_RPC_COMMAND (command speaks line-delimited JSON-RPC 2.0 over stdio)
    """

    def __init__(self) -> None:
        self.command = os.getenv("SYSML_PILOT_COMMAND", "").strip()
        self.rpc_command = os.getenv("SYSML_PILOT_RPC_COMMAND", "").strip()

    def available(self) -> bool:
        return bool(self.rpc_command or self.command)

    def mode(self) -> str:
        if self.rpc_command:
            return "rpc"
        if self.command:
            return "argv"
        return "disabled"

    def capabilities(self) -> dict[str, Any]:
        return {
            "configured": self.available(),
            "mode": self.mode(),
            "env": {
                "SYSML_PILOT_COMMAND": bool(self.command),
                "SYSML_PILOT_RPC_COMMAND": bool(self.rpc_command),
            },
            "notes": [
                "argv mode expects '<cmd> <operation> <workspace>' with JSON payload on stdin",
                "rpc mode expects line-delimited JSON-RPC 2.0 over stdio",
            ],
        }

    def invoke(self, operation: str, workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
        if self.rpc_command:
            return self._invoke_rpc(operation, workspace, payload)
        if self.command:
            return self._invoke_argv(operation, workspace, payload)
        return {
            "ok": False,
            "error": "SYSML_PILOT_COMMAND or SYSML_PILOT_RPC_COMMAND is not configured",
            "operation": operation,
            "capability": "local-fallback-only",
        }

    def _invoke_argv(self, operation: str, workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
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
        return {"ok": True, "result": result, "mode": "argv"}

    def _invoke_rpc(self, operation: str, workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
        argv = shlex.split(self.rpc_command)
        if not argv:
            return {
                "ok": False,
                "error": "SYSML_PILOT_RPC_COMMAND is empty after parsing",
                "operation": operation,
            }

        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": operation,
            "params": {
                "path": str(workspace),
                **payload,
            },
        }
        try:
            proc.stdin.write(json.dumps(req) + "\n")
            proc.stdin.flush()
            line = proc.stdout.readline()
            if not line:
                return {
                    "ok": False,
                    "error": (proc.stderr.read() or "rpc adapter returned no output").strip(),
                    "operation": operation,
                }
            resp = json.loads(line)
            if "error" in resp:
                return {
                    "ok": False,
                    "error": resp["error"].get("message", "rpc adapter error"),
                    "operation": operation,
                    "rpc_error": resp["error"],
                }
            return {"ok": True, "result": resp.get("result"), "mode": "rpc"}
        except json.JSONDecodeError:
            return {
                "ok": False,
                "error": "rpc adapter returned non-JSON output",
                "operation": operation,
            }
        finally:
            try:
                proc.terminate()
            except Exception:  # noqa: BLE001
                pass
