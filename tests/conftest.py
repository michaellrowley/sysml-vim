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

mock_pilot_bridge = Path(__file__).parent / "fixtures" / "mock_pilot_bridge.py"
os.environ.pop("SYSML_PILOT_RPC_COMMAND", None)
os.environ["SYSML_PILOT_COMMAND"] = (
    shlex.join([sys.executable, str(mock_pilot_bridge)])
)
