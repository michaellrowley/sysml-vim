from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
from typing import Any


class ParserBackendError(RuntimeError):
    """Raised when the configured standards parser cannot answer a request."""


class OfficialPilotAdapter:
    """Invoke the configured SysML v2 Pilot bridge.

    The bridge owns the Pilot/Xtext dependency setup; both transports use the
    same JSON contract so the editor backend does not guess at parser behavior.
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
            "expected_parser": "SysML v2 Pilot Implementation",
            "response_validated": False,
            "env": {
                "SYSML_PILOT_COMMAND": bool(self.command),
                "SYSML_PILOT_RPC_COMMAND": bool(self.rpc_command),
            },
            "notes": [
                "argv mode expects '<cmd> <operation> <workspace>' with JSON payload on stdin",
                "rpc mode expects line-delimited JSON-RPC 2.0 over stdio",
                "both modes require a bridge implementing the sysml-vim parse contract",
            ],
        }

    def parse_workspace(self, workspace: Path, files: list[dict[str, str]]) -> dict[str, Any]:
        """Ask the official parser to parse and validate every source file."""
        result = self.invoke("parse", workspace, {"files": files})
        if not result.get("ok"):
            error = result.get("error", "unknown parser adapter error")
            raise ParserBackendError(str(error))
        response = result.get("result")
        if not isinstance(response, dict):
            raise ParserBackendError("parser adapter returned a non-object result")
        return response

    def invoke(self, operation: str, workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
        if self.rpc_command:
            return self._invoke_rpc(operation, workspace, payload)
        if self.command:
            return self._invoke_argv(operation, workspace, payload)
        return {"ok": False, "error": self._configuration_error(), "operation": operation}

    @staticmethod
    def _configuration_error() -> str:
        return (
            "SysML v2 parsing is unavailable: configure SYSML_PILOT_COMMAND or "
            "SYSML_PILOT_RPC_COMMAND with a bridge to the official SysML v2 Pilot parser. "
            "No local subset parser or fallback is provided."
        )

    def _invoke_argv(self, operation: str, workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
        command_arguments = shlex.split(self.command)
        if not command_arguments:
            return {
                "ok": False,
                "error": "SYSML_PILOT_COMMAND is empty after parsing",
                "operation": operation,
            }

        try:
            completed_process = subprocess.run(
                [*command_arguments, operation, str(workspace)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return {
                "ok": False,
                "error": f"parser command failed: {error}",
                "operation": operation,
                "capability": "adapter-error",
            }
        if completed_process.returncode != 0:
            return {
                "ok": False,
                "error": completed_process.stderr.strip()
                or f"command exited with code {completed_process.returncode}",
                "operation": operation,
                "capability": "adapter-error",
            }
        try:
            result = json.loads(completed_process.stdout or "{}")
        except json.JSONDecodeError:
            return {
                "ok": False,
                "error": "adapter returned non-JSON output",
                "stdout": completed_process.stdout[-500:],
                "operation": operation,
            }
        return {"ok": True, "result": result, "mode": "argv"}

    def _invoke_rpc(self, operation: str, workspace: Path, payload: dict[str, Any]) -> dict[str, Any]:
        command_arguments = shlex.split(self.rpc_command)
        if not command_arguments:
            return {
                "ok": False,
                "error": "SYSML_PILOT_RPC_COMMAND is empty after parsing",
                "operation": operation,
            }

        rpc_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": operation,
            "params": {
                "path": str(workspace),
                **payload,
            },
        }
        try:
            # EOF marks the end of this one-request process and lets it exit after its response.
            completed_process = subprocess.run(
                command_arguments,
                input=json.dumps(rpc_request) + "\n",
                text=True,
                capture_output=True,
                check=False,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return {
                "ok": False,
                "error": f"parser RPC command failed: {error}",
                "operation": operation,
                "capability": "adapter-error",
            }
        if completed_process.returncode != 0:
            return {
                "ok": False,
                "error": completed_process.stderr.strip()
                or f"RPC command exited with code {completed_process.returncode}",
                "operation": operation,
                "capability": "adapter-error",
            }
        try:
            response_line = next(
                line for line in completed_process.stdout.splitlines() if line.strip()
            )
            rpc_response = json.loads(response_line)
        except (StopIteration, json.JSONDecodeError):
            return {
                "ok": False,
                "error": "rpc adapter returned no valid JSON response",
                "operation": operation,
            }
        if (
            not isinstance(rpc_response, dict)
            or rpc_response.get("jsonrpc") != "2.0"
            or rpc_response.get("id") != 1
        ):
            return {
                "ok": False,
                "error": "rpc adapter returned a malformed JSON-RPC response",
                "operation": operation,
            }
        if "error" in rpc_response:
            rpc_error = rpc_response["error"]
            if not isinstance(rpc_error, dict):
                return {
                    "ok": False,
                    "error": "rpc adapter returned a malformed error response",
                    "operation": operation,
                }
            return {
                "ok": False,
                "error": rpc_error.get("message", "rpc adapter error"),
                "operation": operation,
                "rpc_error": rpc_error,
            }
        return {"ok": True, "result": rpc_response.get("result"), "mode": "rpc"}
