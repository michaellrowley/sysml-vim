import os
from pathlib import Path
import shlex
import sys


repository_source = str(Path(__file__).parents[1] / "src")
sys.path.insert(0, repository_source)
existing_pythonpath = os.environ.get("PYTHONPATH")
os.environ["PYTHONPATH"] = os.pathsep.join(
    path for path in (repository_source, existing_pythonpath) if path
)

mock_lsp_server = Path(__file__).parent / "fixtures" / "mock_lsp_server.py"
os.environ["SYSML_LSP_COMMAND"] = (
    shlex.join([sys.executable, str(mock_lsp_server)])
)
