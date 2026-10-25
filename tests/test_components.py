"""Include portable component behavior checks in the repository test command."""
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/huawei-html-ppt/scripts'))
from test_diagram_components import ComponentTests  # noqa: F401,E402
