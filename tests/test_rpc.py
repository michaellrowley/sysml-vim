import json
import os
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


def test_rpc_reports_missing_parser_without_fallback():
    environment = os.environ.copy()
    environment.pop("SYSML_LSP_COMMAND", None)
    environment["SYSML_LSP_SERVER"] = "/missing/sysml-lsp/server.js"
    proc = subprocess.Popen(
        [sys.executable, "-m", "sysml_vim.rpc"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    try:
        request = {
            "jsonrpc": "2.0",
            "id": 31,
            "method": "check",
            "params": {"path": "tests/fixtures/workspace"},
        }
        proc.stdin.write(json.dumps(request) + "\n")
        proc.stdin.flush()
        response = json.loads(proc.stdout.readline())
        assert response["error"]["code"] == -32001
        assert "No local subset parser or fallback" in response["error"]["message"]
    finally:
        proc.terminate()


def test_rpc_view_text_and_health_report_parser_capabilities():
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

        graph_req = {
            "jsonrpc": "2.0",
            "id": 23,
            "method": "view_graph",
            "params": {"path": "tests/fixtures/workspace", "type": "composition", "focus": "Vehicle"},
        }
        proc.stdin.write(json.dumps(graph_req) + "\n")
        proc.stdin.flush()
        graph_resp = json.loads(proc.stdout.readline())
        assert "View Graph: composition" in graph_resp["result"]["graph"]

        health_req = {
            "jsonrpc": "2.0",
            "id": 22,
            "method": "health",
            "params": {"path": "tests/fixtures/workspace"},
        }
        proc.stdin.write(json.dumps(health_req) + "\n")
        proc.stdin.flush()
        health_resp = json.loads(proc.stdout.readline())
        assert health_resp["result"]["parser"]["configured"] is True
    finally:
        proc.terminate()
