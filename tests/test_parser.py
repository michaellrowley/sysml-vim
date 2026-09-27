from pathlib import Path

from sysml_vim.model import parse_path


def test_parse_symbols_and_references():
    file_path = Path("tests/fixtures/workspace/vehicle.sysml")
    parsed = parse_path(file_path)
    names = {s.name for s in parsed.symbols}
    assert "Vehicle" in names
    assert "Engine" in names
    ref_names = {r.name for r in parsed.references}
    assert "FuelPort" in ref_names


def test_parse_unclosed_brace_diagnostic():
    file_path = Path("tests/fixtures/workspace/bad.sysml")
    parsed = parse_path(file_path)
    messages = [d.message for d in parsed.diagnostics]
    assert any("Unclosed brace block" in m for m in messages)
