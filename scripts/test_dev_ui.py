import sys
from pathlib import Path
import traceback

sys.path.insert(0, "src")
from python_dev_tool.web.app import create_dev_ui_app

try:
    app = create_dev_ui_app(Path.cwd())
    print("\033[38;5;34m\u2705 Dev UI app creation successful\033[0m")
except Exception as e:
    print(f"\033[38;5;197m\u274c Dev UI app creation failed: {e}\033[0m")
    traceback.print_exc()
    sys.exit(1)
