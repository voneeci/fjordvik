"""Claude Code PreToolUse hook: stop a tool call that would break GUARDRAILS.md.

Claude Code runs this before Bash, PowerShell, Read, Grep, Edit, Write and
NotebookEdit calls in this repository (see .claude/settings.json). It reads the
call as JSON on stdin. Exit code 2 blocks the call and shows the reason; exit
code 0 lets it run.

Rules it enforces (identifiers from GUARDRAILS.md):
  D3  no hand edits to the generated data folders
  D8  no reading or editing a .env file
  G1  commit named paths only
  G2  no hook bypass
  G3  no force push

Maintained by Attena. Other chats suggest changes in guardrails/proposals/.
"""

import json
import re
import sys

GENERATED = ("data/tables/", "data/erp-extract/", "data/corpus/", "data/generator-truth/")
ENV_FILE = re.compile(r"(?<![\w-])\.env(\.(?!example\b)\w+)?(?![\w.-])")
GIT_RULES = [
    ("G1", re.compile(r"\bgit\s+add\s+(?:\S+\s+)*?(-u|-A|--all|--update|\.)(\s|$)"),
     "stage named paths only (git add <path> ...), never -u, -A, --all or '.'"),
    ("G1", re.compile(r"\bgit\s+commit\b.*\s(-[b-zA-Z]*a[a-zA-Z]*|--all)(\s|$)"),
     "commit named paths only, never git commit -a"),
    ("G2", re.compile(r"\bgit\b.*\s--no-verify\b"), "never bypass a git hook"),
    ("G2", re.compile(r"\bgit\s+commit\b.*\s-[a-mo-zA-Z]*n[a-zA-Z]*(\s|$)"),
     "never bypass a git hook (-n skips them)"),
    ("G3", re.compile(r"\bgit\s+push\b.*\s(--force(-with-lease)?|-f)(\s|$)"), "never force push"),
]


def relative(path: str, root: str) -> str:
    p = path.replace("\\", "/")
    r = root.replace("\\", "/").rstrip("/") + "/"
    if p.lower().startswith(r.lower()):
        p = p[len(r):]
    return p.lstrip("./") if p.startswith("./") else p


def is_env_file(path: str) -> bool:
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    return (name == ".env" or name.startswith(".env.")) and name != ".env.example"


def reason(call: dict, root: str) -> str | None:
    tool, args = call.get("tool_name", ""), call.get("tool_input") or {}
    path = args.get("file_path") or args.get("notebook_path") or args.get("path") or ""
    if tool in {"Read", "Grep", "Edit", "Write", "NotebookEdit"} and path and is_env_file(path):
        return "D8: never read or edit a .env file; read settings from environment variables"
    if tool in {"Edit", "Write", "NotebookEdit"} and path:
        rel = relative(path, root)
        if rel.startswith(GENERATED):
            return (f"D3: {rel} is generated; change data/src/fjordvik_data and run "
                    "python -m fjordvik_data --out tables from data/ instead")
    if tool in {"Bash", "PowerShell"}:
        command = args.get("command", "")
        if ENV_FILE.search(command):
            return "D8: never read or touch a .env file; read settings from environment variables"
        for rule, pattern, why in GIT_RULES:
            if pattern.search(command):
                return f"{rule}: {why}"
    return None


def main() -> int:
    try:
        call = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    import os
    root = os.environ.get("CLAUDE_PROJECT_DIR") or call.get("cwd") or os.getcwd()
    why = reason(call, root)
    if why:
        print(f"Blocked by GUARDRAILS.md {why}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
