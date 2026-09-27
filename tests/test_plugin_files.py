from pathlib import Path


def test_plugin_exposes_required_commands():
    plugin = Path("plugin/sysml.vim").read_text(encoding="utf-8")
    for cmd in [
        "SysmlCheck",
        "SysmlCheckWorkspace",
        "SysmlView",
        "SysmlTree",
        "SysmlFind",
        "SysmlDefinition",
        "SysmlReferences",
        "SysmlHealth",
    ]:
        assert cmd in plugin


def test_help_file_exists():
    help_file = Path("doc/sysml-vim.txt")
    assert help_file.exists()
    assert "*sysml-vim-commands*" in help_file.read_text(encoding="utf-8")
