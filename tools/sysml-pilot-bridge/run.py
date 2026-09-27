#!/usr/bin/env python3
"""Run the packaged Pilot bridge from a sysml-vim source checkout."""

from pathlib import Path
import sys


SOURCE_DIRECTORY = Path(__file__).parents[2] / "src"
sys.path.insert(0, str(SOURCE_DIRECTORY))

from sysml_vim.pilot_bridge import main


if __name__ == "__main__":
    raise SystemExit(main())
