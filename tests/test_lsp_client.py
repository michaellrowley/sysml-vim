import os
import sys

import pytest

from sysml_vim.lsp_client import LanguageServerClient, LanguageServerError


def test_client_reaps_server_when_initialization_times_out(tmp_path):
    pid_file = tmp_path / "server.pid"
    server_script = tmp_path / "stalled_server.py"
    server_script.write_text(
        "import os\n"
        "from pathlib import Path\n"
        "import time\n"
        f"Path({str(pid_file)!r}).write_text(str(os.getpid()))\n"
        "time.sleep(60)\n",
        encoding="utf-8",
    )

    with pytest.raises(LanguageServerError, match="timed out"):
        LanguageServerClient(
            [sys.executable, str(server_script)],
            tmp_path,
            timeout=0.5,
        )

    server_process_id = int(pid_file.read_text(encoding="utf-8"))
    with pytest.raises(ProcessLookupError):
        os.kill(server_process_id, 0)


def test_diagnostic_wait_uses_the_configured_client_timeout(monkeypatch):
    client = object.__new__(LanguageServerClient)
    client.timeout = 120.0
    client._diagnostic_notifications = set()
    observed_timeouts = []

    def stop_after_recording_timeout(remaining_timeout):
        observed_timeouts.append(remaining_timeout)
        raise RuntimeError("stop after checking the timeout")

    monkeypatch.setattr(client, "_consume_message", stop_after_recording_timeout)

    with pytest.raises(RuntimeError, match="stop after checking"):
        client._wait_for_diagnostics({"file:///missing.sysml"})

    assert observed_timeouts[0] > 100
