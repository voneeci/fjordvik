"""Claude Code PreToolUse hook: stop a tool call that would break GUARDRAILS.md.

Claude Code runs this before Bash, PowerShell, Monitor, terminal tool
(mcp__terminal__run_in_terminal), Read, Grep, Edit, Write and NotebookEdit calls
in this repository (see .claude/settings.json). It reads the call as JSON on
stdin. Exit code 2 blocks the call and shows the reason; exit code 0 lets it
run, or asks Reece first when it prints an "ask" decision.

Rules it enforces (identifiers from GUARDRAILS.md):
  D2  no chat reads or writes the private banned-names list
  D3  no hand edits or shell writes to the generated data folders
  D8  no reading or editing a .env file (a search pattern on piped file names may name one)
  G1  commit named paths only
  G2  no hook bypass
  G3  no force push
  G9  ask Reece before any edit to the guardrail files
It fails closed: a call it cannot read or check is blocked. The repository root comes
from git (the repository holding this file), not the chat's project folder. Paths are
compared in one form (.. steps resolved, lower case), because Windows file names ignore
case.

Maintained by Attena. Other chats suggest changes in guardrails/proposals/.
"""

import json
import os
import posixpath
import re
import subprocess
import sys

GENERATED = ("data/tables/", "data/erp-extract/", "data/corpus/", "data/generator-truth/")
PROTECTED = ("guardrails.md", "guardrails.sha256", ".claude/settings.json",
             ".claude/settings.local.json")
PROTECTED_DIR, OPEN_DIR = "guardrails/", "guardrails/proposals/"
SHELL_TOOLS = {"Bash", "PowerShell", "Monitor", "mcp__terminal__run_in_terminal"}
ENV_FILE = re.compile(r"(?<![\w-])\.env(\.(?!example\b)\w+)?(?![\w.-])")
# The private list's folder name only when nothing name-like follows it, so a file such
# as 2026-11-02-attena-fjordvik-guardrails-second-edition.md is not mistaken for it.
BANNED_LIST = re.compile(r"(?i)fjordvik-guardrails(?![\w-])|banned-terms")
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
# Commands that write, move or delete the files they name (bash and PowerShell).
WRITERS = re.compile(r"(?i)(^|[\s;(])(tee|sed\s+(-\S+\s+)*-i\S*|set-content|add-content|out-file"
                     r"|new-item|copy-item|move-item|remove-item|rename-item|clear-content"
                     r"|cp|mv|rm|del|erase|copy|move|ren|touch|truncate|sc|ac|ni|cpi|mi|ri)(\s|$)")
SEARCHERS = {"grep", "egrep", "rg", "findstr", "select-string", "sls"}
# Options that make a search read a file rather than its piped input.
FILE_OPTIONS = re.compile(r"(?<!\S)(-[A-Za-z]*f[A-Za-z]*|--file\S*)(?!\S)|(?i:/[gf]:)")
PS_FILE_OPTIONS = re.compile(r"(?i)(?<!\S)-(p(?!attern\b)\w*|l\w*|inputobject\b)")
# A folder name followed by "..", which cancels it (a/../b is b).
PARENT_STEP = re.compile(r"[^\s/'\"]+/\.\./")


def repo_root() -> str:
    """The repository holding this hook, from git; the folder above guardrails/ if git
    can't say."""
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        result = subprocess.run(["git", "-C", here, "rev-parse", "--show-toplevel"],
                                capture_output=True, text=True, timeout=3)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return os.path.dirname(here)


def relative(path: str, root: str) -> str:
    """The path relative to the repository, with .. resolved, in lower case."""
    p = posixpath.normpath(path.replace("\\", "/"))
    r = posixpath.normpath(root.replace("\\", "/")) + "/"
    if p.lower().startswith(r.lower()):
        p = p[len(r):]
    return p.lower()


def is_env_file(path: str) -> bool:
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    return (name == ".env" or name.startswith(".env.")) and name != ".env.example"


def is_protected(rel: str) -> bool:
    return rel in PROTECTED or (rel.startswith(PROTECTED_DIR) and not rel.startswith(OPEN_DIR))


def split_command(command: str) -> list[list[tuple[str, list[tuple[int, int]]]]]:
    """Split a shell command into commands (on ; && || and new lines), each a list of
    pipe stages. Each stage is (text, quoted spans within it). Quotes are tracked on the
    raw text, so Windows paths such as mcp\\.env keep their backslashes."""
    commands, stages, start, quote, spans, open_at, i = [], [], 0, "", [], 0, 0

    def close(end: int) -> None:
        stages.append((command[start:end], [(a - start, b - start) for a, b in spans]))

    while i < len(command):
        ch = command[i]
        if quote:
            if ch == quote:
                spans.append((open_at, i + 1))
                quote = ""
        elif ch in "'\"":
            quote, open_at = ch, i
        elif command.startswith(("&&", "||"), i) or ch in ";\n|":
            close(i)
            step = 2 if command.startswith(("&&", "||"), i) else 1
            if ch != "|" or step == 2:
                commands.append(stages)
                stages = []
            start, spans, i = i + step, [], i + step
            continue
        i += 1
    if quote:
        spans.append((open_at, len(command)))
    close(len(command))
    commands.append(stages)
    return commands


def first_word(stage: str) -> str:
    words = stage.split()
    return words[0].lower() if words else ""


def safe_env_search(stage: str, spans: list[tuple[int, int]], index: int) -> bool:
    """True when every .env mention is a quoted search pattern applied to piped input."""
    word = first_word(stage)
    if index == 0 or word not in SEARCHERS:
        return False
    if "$(" in stage or "`" in stage or "<" in stage or FILE_OPTIONS.search(stage):
        return False
    if word in {"select-string", "sls"} and PS_FILE_OPTIONS.search(stage):
        return False
    return all(any(a < m.start() and m.end() <= b for a, b in spans)
               for m in ENV_FILE.finditer(stage))


def normal_stage(stage: str) -> str:
    """A shell stage in the same form as relative(): forward slashes, .. steps resolved,
    lower case."""
    text = stage.replace("\\", "/").lower()
    while PARENT_STEP.search(text):
        text = PARENT_STEP.sub("", text, count=1)
    return text


def writes_to(stage: str, folders: tuple[str, ...]) -> bool:
    """True when a shell stage writes into one of the named paths: a redirect into one,
    or a writing command (cp, rm, Set-Content and so on) that names one."""
    text = normal_stage(stage)
    if first_word(text) == "git":
        return False
    names = "|".join(re.escape(f.rstrip("/").lower()) for f in folders)
    end = r"(?=[/\s'\"]|$)"
    if re.search(rf"(?<![0-9&])>>?\s*['\"]?(\S*/)?({names}){end}", text):
        return True
    return bool(WRITERS.search(text)) and bool(re.search(rf"(^|[\s'\"/=])({names}){end}", text))


def shell_reason(command: str, cwd_rel: str) -> str | None:
    generated = GENERATED
    if cwd_rel == "data" or cwd_rel.startswith("data/") or re.search(
            r"(?i)\b(cd|set-location|push-location|pushd)\s+['\"]?\.?/?data\b", command):
        generated = GENERATED + tuple(g[len("data/"):] for g in GENERATED)
    ask = False
    for stages in split_command(command):
        for index, (stage, spans) in enumerate(stages):
            if ENV_FILE.search(stage) and not safe_env_search(stage, spans, index):
                return "D8: never read or touch a .env file; read settings from environment variables"
            if writes_to(stage, generated):
                return ("D3: the generated data folders change only through the generator "
                        "(python -m fjordvik_data --out tables, from data/)")
            outside_proposals = re.sub(r"guardrails/proposals/\S*", "", normal_stage(stage))
            if writes_to(outside_proposals, PROTECTED + (PROTECTED_DIR,)):
                ask = True
    for rule, pattern, why in GIT_RULES:
        if pattern.search(command):
            return f"{rule}: {why}"
    return "ask" if ask else None


def shell_cwd(call: dict, args: dict, root: str) -> str:
    """The folder a shell command runs in: the call's own, or for the terminal tool its
    cwd argument (absolute, ~ or relative to the call's folder)."""
    cwd = call.get("cwd") or root
    if call.get("tool_name") == "mcp__terminal__run_in_terminal" and args.get("cwd"):
        cwd = os.path.join(cwd, os.path.expanduser(args["cwd"]))
    return cwd


def reason(call: dict, root: str) -> str | None:
    """None to allow, "ask" to ask Reece, or the reason to block."""
    tool, args = call.get("tool_name", ""), call.get("tool_input") or {}
    path = args.get("file_path") or args.get("notebook_path") or args.get("path") or ""
    command = args.get("command") or "" if tool in SHELL_TOOLS else ""
    if BANNED_LIST.search(path) or BANNED_LIST.search(command):
        return "D2: only Reece reads or writes the private banned-names list"
    if tool in {"Read", "Grep", "Edit", "Write", "NotebookEdit"} and path and is_env_file(path):
        return "D8: never read or edit a .env file; read settings from environment variables"
    if tool in {"Edit", "Write", "NotebookEdit"} and path:
        rel = relative(path, root)
        if rel.startswith(GENERATED):
            return (f"D3: {rel} is generated; change data/src/fjordvik_data and run "
                    "python -m fjordvik_data --out tables from data/ instead")
        if is_protected(rel):
            return "ask"
    if command:
        cwd = relative(shell_cwd(call, args, root), root).rstrip("/")
        return shell_reason(command, cwd)
    return None


def main() -> int:
    try:
        call = json.load(sys.stdin)
        why = reason(call, repo_root())
    except Exception as error:  # fail closed: a call the hook can't check doesn't run
        print(f"Blocked by GUARDRAILS.md: the guardrail hook could not check this call "
              f"({type(error).__name__}).", file=sys.stderr)
        return 2
    if why == "ask":
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": "GUARDRAILS.md G9: only Attena edits the guardrail "
                                        "files. Approve only in the Attena chat."}}))
        return 0
    if why:
        print(f"Blocked by GUARDRAILS.md {why}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
