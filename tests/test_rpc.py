import json
import subprocess
import sys


def test_rpc_definition():
    proc = subprocess.Popen(
        [sys.executable, "-m", "sysml_vim.rpc"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "definition",
            "params": {"path": "tests/fixtures/workspace", "name": "Vehicle"},
        }
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        resp = json.loads(line)
        assert resp["result"]["name"] == "Vehicle"

        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": {}}) + "\n")
        proc.stdin.flush()
    finally:
        proc.terminate()
