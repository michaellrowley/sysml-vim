from __future__ import annotations

from collections import deque
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
from typing import Any
from urllib.parse import unquote, urlparse


class LanguageServerError(RuntimeError):
    """Raised when the configured SysML language server cannot answer."""


class LanguageServerClient:
    """Synchronous client for the SysML LSP server's stdio transport."""

    def __init__(self, command: list[str], workspace: Path, timeout: float = 120.0):
        self.command = command
        self.workspace = workspace.resolve()
        self.timeout = timeout
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=-1,
        )
        self._messages: queue.Queue[dict[str, Any] | BaseException] = queue.Queue()
        self._write_lock = threading.Lock()
        self._request_lock = threading.Lock()
        self._stderr_lines: deque[str] = deque(maxlen=30)
        self._diagnostics: dict[str, list[dict[str, Any]]] = {}
        self._diagnostic_notifications: set[str] = set()
        self._documents: dict[str, tuple[int, str]] = {}
        self._next_request_id = 0
        self._closed = False
        self._reader_threads = [
            threading.Thread(target=self._read_messages, daemon=True),
            threading.Thread(target=self._read_stderr, daemon=True),
        ]

        try:
            for reader_thread in self._reader_threads:
                reader_thread.start()
            self._initialize()
        except BaseException:
            self._terminate_process()
            for reader_thread in self._reader_threads:
                if reader_thread.ident is not None:
                    reader_thread.join(timeout=1)
            raise

    def _initialize(self) -> None:
        workspace_uri = self.workspace.as_uri()
        self.request(
            "initialize",
            {
                "processId": os.getpid(),
                "rootUri": workspace_uri,
                "workspaceFolders": [
                    {"uri": workspace_uri, "name": self.workspace.name or "workspace"}
                ],
                "capabilities": {
                    "workspace": {
                        "configuration": False,
                        "workspaceFolders": True,
                    },
                    "textDocument": {
                        "documentSymbol": {
                            "hierarchicalDocumentSymbolSupport": True,
                        },
                        "publishDiagnostics": {
                            "relatedInformation": True,
                        },
                    },
                },
            },
        )
        self.notify("initialized", {})

    def update_workspace(
        self,
        files: list[dict[str, str]],
    ) -> dict[str, dict[str, Any]]:
        """Open or update all model documents, then ask the server for projections."""
        desired_documents = {
            Path(source["path"]).resolve().as_uri(): (
                Path(source["path"]).resolve(),
                source["text"],
            )
            for source in files
        }
        for document_uri in self._documents.keys() - desired_documents.keys():
            self.notify("textDocument/didClose", {"textDocument": {"uri": document_uri}})
            self._documents.pop(document_uri, None)
            self._diagnostics.pop(document_uri, None)
            self._diagnostic_notifications.discard(document_uri)

        for document_uri, (source_path, source_text) in desired_documents.items():
            cached_document = self._documents.get(document_uri)
            if cached_document is None:
                version = 1
                self._diagnostics.pop(document_uri, None)
                self._diagnostic_notifications.discard(document_uri)
                self.notify(
                    "textDocument/didOpen",
                    {
                        "textDocument": {
                            "uri": document_uri,
                            "languageId": "sysml" if source_path.suffix.lower() == ".sysml" else "kerml",
                            "version": version,
                            "text": source_text,
                        }
                    },
                )
            elif cached_document[1] != source_text:
                version = cached_document[0] + 1
                self._diagnostics.pop(document_uri, None)
                self._diagnostic_notifications.discard(document_uri)
                self.notify(
                    "textDocument/didChange",
                    {
                        "textDocument": {"uri": document_uri, "version": version},
                        "contentChanges": [{"text": source_text}],
                    },
                )
            else:
                continue
            self._documents[document_uri] = (version, source_text)

        projections: dict[str, dict[str, Any]] = {}
        for document_uri, (source_path, _) in desired_documents.items():
            model_result = self.request(
                "sysml/model",
                {
                    "textDocument": {"uri": document_uri},
                    "scope": ["elements", "relationships", "diagnostics"],
                },
            )
            if not isinstance(model_result, dict):
                raise LanguageServerError(
                    f"language server returned no model projection for {source_path}"
                )
            expected_version = self._documents[document_uri][0]
            if model_result.get("version") != expected_version:
                raise LanguageServerError(
                    f"language server returned a stale model for {source_path}"
                )

            document_symbols = self.request(
                "textDocument/documentSymbol",
                {"textDocument": {"uri": document_uri}},
            )
            if document_symbols is None:
                document_symbols = []
            if not isinstance(document_symbols, list):
                raise LanguageServerError(
                    f"language server returned invalid document symbols for {source_path}"
                )
            projections[str(source_path)] = {
                "model": model_result,
                "document_symbols": document_symbols,
                "uri": document_uri,
            }

        self._wait_for_diagnostics(set(desired_documents))
        for projection in projections.values():
            projection["diagnostics"] = self._diagnostics.get(projection["uri"], [])
        return projections

    def references(self, document_uri: str, position: dict[str, int]) -> list[dict[str, Any]]:
        result = self.request(
            "textDocument/references",
            {
                "textDocument": {"uri": document_uri},
                "position": position,
                "context": {"includeDeclaration": False},
            },
        )
        if result is None:
            return []
        if not isinstance(result, list) or any(not isinstance(item, dict) for item in result):
            raise LanguageServerError("language server returned invalid reference locations")
        return result

    def _wait_for_diagnostics(self, document_uris: set[str]) -> None:
        missing_uris = document_uris - self._diagnostic_notifications
        deadline = time.monotonic() + self.timeout
        while missing_uris:
            remaining_time = deadline - time.monotonic()
            if remaining_time <= 0:
                paths = ", ".join(
                    Path(unquote(urlparse(uri).path)).name
                    for uri in sorted(missing_uris)
                )
                raise LanguageServerError(
                    "language server did not publish diagnostics for: " + paths
                )
            self._consume_message(remaining_time)
            missing_uris = document_uris - self._diagnostic_notifications

        # Coalesce duplicate and cross-file updates so the index keeps the latest diagnostics.
        quiet_deadline = time.monotonic() + 0.15
        while True:
            remaining_time = quiet_deadline - time.monotonic()
            if remaining_time <= 0:
                return
            try:
                message = self._messages.get(timeout=remaining_time)
            except queue.Empty:
                return
            if isinstance(message, BaseException):
                raise LanguageServerError(str(message)) from message
            self._handle_message(message)
            quiet_deadline = time.monotonic() + 0.15

    def request(self, method: str, parameters: dict[str, Any]) -> Any:
        with self._request_lock:
            self._next_request_id += 1
            request_id = self._next_request_id
            self._send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": method,
                    "params": parameters,
                }
            )
            deadline = time.monotonic() + self.timeout
            while True:
                remaining_time = deadline - time.monotonic()
                if remaining_time <= 0:
                    raise LanguageServerError(
                        f"timed out waiting for language server method {method!r}"
                    )
                message = self._next_message(remaining_time)
                if message.get("id") == request_id:
                    if "error" in message:
                        error = message["error"]
                        if not isinstance(error, dict):
                            raise LanguageServerError(
                                f"language server returned an invalid error for {method!r}"
                            )
                        raise LanguageServerError(
                            str(error.get("message", f"language server rejected {method!r}"))
                        )
                    if "result" not in message:
                        raise LanguageServerError(
                            f"language server returned no result for {method!r}"
                        )
                    return message["result"]
                self._handle_message(message)

    def notify(self, method: str, parameters: dict[str, Any]) -> None:
        self._send(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": parameters,
            }
        )

    def _send(self, message: dict[str, Any]) -> None:
        if self.process.poll() is not None:
            raise self._server_exited_error()
        encoded_body = json.dumps(message, separators=(",", ":")).encode("utf-8")
        framed_message = (
            f"Content-Length: {len(encoded_body)}\r\n\r\n".encode("ascii")
            + encoded_body
        )
        try:
            with self._write_lock:
                if self.process.stdin is None:
                    raise BrokenPipeError("language server stdin is closed")
                self.process.stdin.write(framed_message)
                self.process.stdin.flush()
        except OSError as error:
            raise LanguageServerError(
                f"could not send a request to the SysML language server: {error}"
            ) from error

    def _read_messages(self) -> None:
        try:
            if self.process.stdout is None:
                raise LanguageServerError("language server stdout is unavailable")
            while True:
                headers: dict[str, str] = {}
                while True:
                    header_line = self.process.stdout.readline()
                    if not header_line:
                        raise self._server_exited_error()
                    if header_line in {b"\r\n", b"\n"}:
                        break
                    header_name, separator, header_value = header_line.decode(
                        "ascii", errors="replace"
                    ).partition(":")
                    if separator:
                        headers[header_name.strip().lower()] = header_value.strip()

                try:
                    content_length = int(headers["content-length"])
                except (KeyError, ValueError) as error:
                    raise LanguageServerError(
                        "language server sent an invalid Content-Length header"
                    ) from error
                if content_length < 0 or content_length > 64 * 1024 * 1024:
                    raise LanguageServerError(
                        "language server response exceeded the 64 MiB message limit"
                    )
                message_body = self.process.stdout.read(content_length)
                if len(message_body) != content_length:
                    raise LanguageServerError("language server closed during a response")
                message = json.loads(message_body.decode("utf-8"))
                if not isinstance(message, dict):
                    raise LanguageServerError("language server sent a non-object message")
                self._messages.put(message)
        except Exception as error:
            self._messages.put(error)

    def _read_stderr(self) -> None:
        if self.process.stderr is None:
            return
        for line in self.process.stderr:
            self._stderr_lines.append(line.decode("utf-8", errors="replace").rstrip())

    def _next_message(self, timeout: float) -> dict[str, Any]:
        try:
            message = self._messages.get(timeout=timeout)
        except queue.Empty as error:
            raise LanguageServerError("timed out waiting for the SysML language server") from error
        if isinstance(message, BaseException):
            raise LanguageServerError(str(message)) from message
        return message

    def _consume_message(self, timeout: float) -> None:
        message = self._next_message(timeout)
        self._handle_message(message)

    def _handle_message(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        parameters = message.get("params")
        if method == "textDocument/publishDiagnostics" and isinstance(parameters, dict):
            document_uri = parameters.get("uri")
            diagnostics = parameters.get("diagnostics")
            if isinstance(document_uri, str) and isinstance(diagnostics, list):
                self._diagnostics[document_uri] = diagnostics
                self._diagnostic_notifications.add(document_uri)
            return

        if method and "id" in message:
            # The server may ask for optional client configuration or progress support.
            result: Any = None
            if method == "workspace/configuration":
                items = parameters.get("items", []) if isinstance(parameters, dict) else []
                result = [None] * len(items)
            elif method == "workspace/workspaceFolders":
                result = [
                    {"uri": self.workspace.as_uri(), "name": self.workspace.name or "workspace"}
                ]
            self._send({"jsonrpc": "2.0", "id": message["id"], "result": result})

    def _server_exited_error(self) -> LanguageServerError:
        exit_status = self.process.poll()
        stderr_tail = "\n".join(self._stderr_lines).strip()
        details = f" (exit code {exit_status})" if exit_status is not None else ""
        if stderr_tail:
            details += f": {stderr_tail}"
        return LanguageServerError("SysML language server exited" + details)

    def _terminate_process(self) -> None:
        if self.process.poll() is None:
            try:
                self.process.terminate()
            except ProcessLookupError:
                pass
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    self.process.kill()
                except ProcessLookupError:
                    pass
                self.process.wait(timeout=5)
        else:
            self.process.wait()
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream is not None and not stream.closed:
                stream.close()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self.process.poll() is None:
            try:
                self.request("shutdown", {})
                self.notify("exit", {})
            except LanguageServerError:
                self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream is not None and not stream.closed:
                stream.close()
