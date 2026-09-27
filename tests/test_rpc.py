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


def test_rpc_unknown_method_returns_error():
    proc = subprocess.Popen(
        [sys.executable, "-m", "sysml_vim.rpc"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        req = {"jsonrpc": "2.0", "id": 11, "method": "unknown_method", "params": {}}
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        resp = json.loads(proc.stdout.readline())
        assert resp["error"]["code"] == -32601
    finally:
        proc.terminate()


def test_rpc_missing_params_returns_invalid_params():
    proc = subprocess.Popen(
        [sys.executable, "-m", "sysml_vim.rpc"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        req = {"jsonrpc": "2.0", "id": 12, "method": "definition", "params": {}}
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        resp = json.loads(proc.stdout.readline())
        assert resp["error"]["code"] == -32602
    finally:
        proc.terminate()


def test_rpc_view_text_and_health_include_adapter_capabilities():
    proc = subprocess.Popen(
        [sys.executable, "-m", "sysml_vim.rpc"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        view_req = {
            "jsonrpc": "2.0",
            "id": 21,
            "method": "view_text",
            "params": {"path": "tests/fixtures/workspace", "type": "requirements"},
        }
        proc.stdin.write(json.dumps(view_req) + "\n")
        proc.stdin.flush()
        view_resp = json.loads(proc.stdout.readline())
        assert "View: requirements" in view_resp["result"]["text"]

        health_req = {
            "jsonrpc": "2.0",
            "id": 22,
            "method": "health",
            "params": {"path": "tests/fixtures/workspace"},
        }
        proc.stdin.write(json.dumps(health_req) + "\n")
        proc.stdin.flush()
        health_resp = json.loads(proc.stdout.readline())
        assert "official_adapter" in health_resp["result"]
    finally:
        proc.terminate()
