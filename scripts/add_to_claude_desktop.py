"""Add the fjordvik server to Claude Desktop's configuration.

Run this with Claude Desktop fully closed (quit it from the system tray first).
Claude Desktop rewrites its configuration file when it quits, so an edit made
while it is running is lost.

Usage:  python scripts/add_to_claude_desktop.py           (add the entry)
        python scripts/add_to_claude_desktop.py --remove  (take it out again)

A dated backup of the configuration is made before any change. Other settings
in the file are kept as they are.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONFIG = Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
PYTHON = REPO / ".venv" / "Scripts" / "python.exe"


def claude_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq claude.exe"],
                         capture_output=True, text=True).stdout
    return "claude.exe" in out.lower()


def main() -> int:
    remove = "--remove" in sys.argv
    if claude_running():
        print("Claude Desktop is still running. Quit it from the system tray "
              "(right-click the Claude icon, Quit), then run this again.")
        return 1
    if not remove and not PYTHON.exists():
        print(f"Not found: {PYTHON}. Create the virtual environment first (see README).")
        return 1

    config = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    if CONFIG.exists():
        backup = CONFIG.with_name(f"{CONFIG.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
        shutil.copyfile(CONFIG, backup)
        print(f"Backup: {backup}")

    servers = config.setdefault("mcpServers", {})
    if remove:
        servers.pop("fjordvik", None)
    else:
        servers["fjordvik"] = {"command": str(PYTHON), "args": ["-m", "fjordvik_mcp"]}

    CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
    check = json.loads(CONFIG.read_text(encoding="utf-8"))
    print(f"Done. MCP servers now in the config: {list(check.get('mcpServers', {}))}")
    print("Open Claude Desktop again; fjordvik should appear under Connectors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
