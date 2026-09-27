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
