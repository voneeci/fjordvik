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
  G2  no hook bypass, no change to the hooks setting
  G3  no force push
  G9  ask Reece before any edit to the guardrail files
It fails closed: a call it cannot read or check is blocked. The repository root comes
from git (the repository holding this file), not the chat's project folder. Paths are
compared in one form (.. steps resolved, lower case), because Windows file names ignore
case; file paths are first made canonical (prefixes, stream names, trailing dots and
short names removed). Shell commands are checked from the folder they run in, following
cd through the command. GUARDRAILS.sha256 fingerprints this file, so an edit the hook
misses still fails the tests.

Maintained by Attena. Other chats suggest changes in guardrails/proposals/.
"""

import fnmatch
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
ENV_FILE = re.compile(r"(?i)(?<![\w-])\.env(\.(?!example\b)\w+)?(?![\w.-])")
# The private list's folder name only when nothing name-like follows it, so a file such
# as 2026-11-02-attena-fjordvik-guardrails-second-edition.md is not mistaken for it.
BANNED_LIST = re.compile(r"(?i)fjordvik-guardrails(?![\w-])|banned-terms")
BANNED_NAMES = ("fjordvik-guardrails", "banned-terms.txt")
# git's options that come before the subcommand, dropped so "git -C . add -A" reads as
# "git add -A".
GIT_GLOBAL = re.compile(r"(?i)\bgit((?:\s+(?:-C\s+(?:'[^']*'|\"[^\"]*\"|\S+)|-c\s+\S+"
                        r"|--git-dir(?:=|\s+)\S+|--work-tree(?:=|\s+)\S+|--namespace(?:=|\s+)\S+"
                        r"|--no-pager|-P|--bare|--no-replace-objects|--no-optional-locks"
                        r"|--(?:no-)?(?:literal|glob|noglob|icase)-pathspecs))+)(?=\s)")
HOOKS_SETTING = re.compile(r"(?i)core\.hookspath")
GIT_RULES = [
    ("G1", re.compile(r"\bgit\s+(?:add|stage)\s+(?:\S+\s+)*?(-u|-A|--all|--al|--a|--update|--u\w*"
                      r"|--no-ignore-removal|-[a-zA-Z]*[Au][a-zA-Z]*|\.|\./|\*|:/\S*)(\s|$)"),
     "stage named paths only (git add <path> ...), never -u, -A, --all, '.', '*' or ':/'"),
    ("G1", re.compile(r"\bgit\s+commit\b.*\s(-[b-zA-Z]*a[a-zA-Z]*|--all?)(\s|$)"),
     "commit named paths only, never git commit -a"),
    ("G2", re.compile(r"\bgit\b.*\s--no-veri\w*"), "never bypass a git hook"),
    ("G2", re.compile(r"\bgit\s+commit\b.*\s-[a-mo-zA-Z]*n[a-zA-Z]*(\s|$)"),
     "never bypass a git hook (-n skips them)"),
    ("G3", re.compile(r"\bgit\s+push\b.*\s(--for\w*(-with-lease\S*)?|--force\S*"
                      r"|-[a-zA-Z]*f[a-zA-Z]*|\+\S+)(\s|$)"), "never force push"),
]
# Commands that write, move or delete the files they name (bash and PowerShell).
WRITERS = re.compile(r"(?i)(^|[\s;(])(tee|sed\s+(-\S+\s+)*-i\S*|set-content|add-content|out-file"
                     r"|new-item|copy-item|move-item|remove-item|rename-item|clear-content"
                     r"|export-csv|epcsv|export-clixml|robocopy|xcopy|tar|dd|install|unlink"
                     r"|cp|mv|rm|rmdir|rd|del|erase|copy|move|ren|touch|truncate|sc|ac|ni|cpi"
                     r"|mi|ri)(\s|$)")
DELETERS = {"rm", "rmdir", "rd", "del", "erase", "remove-item", "ri", "unlink"}
# Code run inline that writes or deletes files.
PY_WRITE = re.compile(r"(?i)\bpy(?:thon)?3?(?:\.exe)?\b[^|;&]*\s-c\b.*(open\([^)]*['\"][wax]"
                      r"|write_text|write_bytes|to_csv|to_parquet|to_excel|to_json|shutil\."
                      r"|os\.remove|unlink\(|rmtree|rename\()")
IO_WRITE = re.compile(r"(?i)\[(?:system\.)?io\.(?:file|directory)\]::"
                      r"(write|append|delete|copy|move|create|replace)")
GIT_WRITES = {"rm", "mv", "checkout", "restore", "apply", "clean"}
CD_WORDS = {"cd", "chdir", "set-location", "sl", "pushd", "push-location"}
REDIRECT = re.compile(r"(?<![>&-])>>?\s*(['\"]?)([^\s'\";|&]+)")
NULL_TARGETS = {"/dev/null", "$null", "nul", "null"}
SEARCHERS = {"grep", "egrep", "rg", "findstr", "select-string", "sls"}
# Options that make a search read a file rather than its piped input.
FILE_OPTIONS = re.compile(r"(?<!\S)(-[A-Za-z]*f[A-Za-z]*|--file\S*)(?!\S)|(?i:/[gf]:)")
PS_FILE_OPTIONS = re.compile(r"(?i)(?<!\S)-(p(?!attern\b)\w*|l\w*|inputobject\b)")
# A folder name followed by "..", which cancels it (a/../b is b).
PARENT_STEP = re.compile(r"[^\s/'\"]+/\.\./")
TOKEN = re.compile(r"'[^']*'|\"[^\"]*\"|\S+")


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


def canonical(path: str, cwd: str) -> str:
    """One Windows form of a file path: no \\\\?\\ or admin-share prefix, no stream names,
    no trailing dots or spaces, joined to the call's folder when relative, with 8.3
    short names written out in full."""
    p = path.replace("/", "\\")
    if re.match(r"(?i)^\\\\\?\\unc\\", p):
        p = "\\\\" + p[8:]
    if re.match(r"^\\\\[?.]\\", p):
        p = p[4:]
    share = re.match(r"(?i)^\\\\(?:localhost|127\.0\.0\.1)\\([a-z])\$(\\.*)?$", p)
    if share:
        p = f"{share.group(1)}:{share.group(2) or chr(92)}"
    bash = re.match(r"^\\([a-zA-Z])(\\.*)?$", p)
    if bash:
        p = f"{bash.group(1)}:{bash.group(2) or chr(92)}"
    drive, rest = (p[:2], p[2:]) if re.match(r"^[a-zA-Z]:", p) else ("", p)
    parts = [s if s in (".", "..") else s.split(":", 1)[0].rstrip(". ") for s in rest.split("\\")]
    p = drive + "\\".join(parts)
    if not drive and not p.startswith("\\"):
        p = os.path.join(cwd, p)
    p = os.path.normpath(p)
    if "~" in p:
        head, tail = p, []
        while head and not os.path.exists(head):
            head, part = os.path.split(head)
            if not part:
                break
            tail.insert(0, part)
        if head and os.path.exists(head):
            p = os.path.join(os.path.realpath(head), *tail)
    return p


def is_env_file(path: str) -> bool:
    name = path.replace("\\", "/").rsplit("/", 1)[-1].lower()
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


def git_normal(text: str) -> str:
    """git commands with their global options dropped."""
    return GIT_GLOBAL.sub("git", text)


def glob_names(stage: str, spans: list[tuple[int, int]], names: tuple[str, ...]) -> bool:
    """True when an unquoted wildcard word in the stage would match one of the names:
    .e* or .en[v] for .env, banned* for the private list. Words must start with a dot
    or three letters, so * and *.txt on their own don't count."""
    for m in re.finditer(r"\S+", stage):
        if any(a <= m.start() < b for a, b in spans):
            continue
        word = m.group(0).replace("\\", "/").rstrip(";)").rsplit("/", 1)[-1].lower()
        if not re.search(r"[*?\[]", word) or not re.match(r"^(\.|[^*?\[]{3})", word):
            continue
        if any(fnmatch.fnmatchcase(n, word) for n in names):
            return True
    return False


def in_repo(path: str, root: str) -> list[str] | None:
    """The path's folders inside the repository, in lower case; None when outside."""
    p = posixpath.normpath(path.replace("\\", "/")).lower()
    r = posixpath.normpath(root.replace("\\", "/")).lower()
    if p == r:
        return []
    if p.startswith(r + "/"):
        return p[len(r) + 1:].split("/")
    return None


def as_path(word: str, cwd: str) -> str | None:
    """A shell word as an absolute path, or None when it can't name a file here."""
    word = word.strip("'\"").replace("\\", "/")
    if "=" in word and not word.startswith("="):
        word = word.split("=", 1)[1]
    if not word or word[0] in "-$~&%@" or word.lower() in NULL_TARGETS:
        return None
    drive = re.match(r"^/([a-zA-Z])(/.*)?$", word)
    if drive:
        word = f"{drive.group(1)}:{drive.group(2) or '/'}"
    elif word.startswith("/"):
        return None
    return canonical(word, cwd)


def place(segments: list[str], target: str) -> str:
    """How path segments (which may hold wildcards) relate to a repository path: "in"
    (inside it or the same), "above" (a parent of it) or ""."""
    parts = target.rstrip("/").split("/")
    shared = min(len(segments), len(parts))
    if not all(fnmatch.fnmatchcase(parts[i], segments[i]) for i in range(shared)):
        return ""
    return "in" if len(segments) >= len(parts) else "above"


def judge(segments: list[str], deleting: bool) -> str | None:
    """block (generated data), ask (guardrail files) or None for one path a shell
    command writes."""
    for g in GENERATED:
        where = place(segments, g)
        if where == "in" or (where == "above" and deleting):
            return "block"
    in_open = place(segments, OPEN_DIR) == "in"
    for p in PROTECTED + (PROTECTED_DIR,):
        where = place(segments, p)
        if (where == "in" and not in_open) or (where == "above" and deleting):
            return "ask"
    return None


def stage_verdict(stage: str, cwd: str, root: str) -> str | None:
    """block, ask or None for one pipe stage run in the folder cwd."""
    words = [m.group(0) for m in TOKEN.finditer(stage)]
    if not words:
        return None
    command = words[0].strip("'\"").replace("\\", "/").rsplit("/", 1)[-1].lower()
    command = command[:-4] if command.endswith(".exe") else command
    targets = [m.group(2) for m in REDIRECT.finditer(stage)]
    paths, deleting = list(targets), False
    if command == "git":
        inside = re.match(r"(?i)\S+\s+-C\s+(['\"]?)(\S+?)\1(\s|$)", stage)
        cwd = (as_path(inside.group(2), cwd) or cwd) if inside else cwd
        flat = git_normal(stage).split()
        if len(flat) > 1 and flat[1].lower() in GIT_WRITES:
            for word in flat[2:]:
                path = as_path(word, cwd)
                segments = in_repo(path, root) if path else None
                if segments is not None and judge(segments, True) == "ask":
                    return "ask"
        return None
    if WRITERS.search(stage):
        paths += words[1:]
        deleting = command in DELETERS
    inline = PY_WRITE.search(stage) or IO_WRITE.search(stage)
    worst = None
    for word in paths:
        path = as_path(word, cwd)
        segments = in_repo(path, root) if path else None
        if segments is None:
            continue
        verdict = judge(segments, deleting)
        if verdict == "block":
            return "block"
        worst = worst or verdict
    if inline:
        here = in_repo(cwd, root)
        text = normal_stage(stage)
        if here is not None and judge(here, False) == "block" or any(
                g.rstrip("/") in text for g in GENERATED):
            return "block"
        if here is not None and judge(here, False) == "ask" or any(
                p.rstrip("/") in text for p in PROTECTED + (PROTECTED_DIR,)):
            worst = worst or "ask"
    return worst


def step_into(cwd: str, stage: str) -> str:
    """The folder after a cd, Set-Location or pushd stage; unchanged otherwise."""
    words = [w.strip("'\"") for w in stage.split()]
    if not words or words[0].lower() not in CD_WORDS:
        return cwd
    args = [w for w in words[1:] if not w.startswith("-")]
    if not args:
        return cwd
    path = as_path(args[0], cwd)
    return path if path else cwd


def shell_reason(command: str, cwd: str, root: str) -> str | None:
    """None to allow, "ask" or the reason to block, for a shell command run in cwd."""
    if HOOKS_SETTING.search(command):
        return "G2: never change the git hooks setting; only Reece does, by hand"
    ask = False
    for stages in split_command(command):
        for index, (stage, spans) in enumerate(stages):
            if (ENV_FILE.search(stage) and not safe_env_search(stage, spans, index)) or \
                    glob_names(stage, spans, (".env", ".env.local")):
                return "D8: never read or touch a .env file; read settings from environment variables"
            if glob_names(stage, spans, BANNED_NAMES):
                return "D2: only Reece reads or writes the private banned-names list"
            verdict = stage_verdict(stage, cwd, root)
            if verdict == "block":
                return ("D3: the generated data folders change only through the generator "
                        "(python -m fjordvik_data --out tables, from data/)")
            ask = ask or verdict == "ask"
            if index == 0:
                cwd = step_into(cwd, stage)
    flat = git_normal(command)
    for rule, pattern, why in GIT_RULES:
        if pattern.search(flat):
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
    raw = args.get("file_path") or args.get("notebook_path") or args.get("path") or ""
    command = (args.get("command") or "") if tool in SHELL_TOOLS else ""
    path = canonical(raw, call.get("cwd") or root) if raw else ""
    pattern = (args.get("glob") or "") if tool == "Grep" else ""
    if BANNED_LIST.search(raw) or BANNED_LIST.search(path) or BANNED_LIST.search(command) \
            or BANNED_LIST.search(pattern) or glob_names(pattern, [], BANNED_NAMES):
        return "D2: only Reece reads or writes the private banned-names list"
    if tool in {"Read", "Grep", "Edit", "Write", "NotebookEdit"} and (
            (path and is_env_file(path)) or ENV_FILE.search(pattern)
            or glob_names(pattern, [], (".env", ".env.local"))):
        return "D8: never read or edit a .env file; read settings from environment variables"
    if tool in {"Edit", "Write", "NotebookEdit"} and path:
        rel = relative(path, root)
        if rel.startswith(GENERATED):
            return (f"D3: {rel} is generated; change data/src/fjordvik_data and run "
                    "python -m fjordvik_data --out tables from data/ instead")
        if is_protected(rel):
            return "ask"
    if command:
        return shell_reason(command, shell_cwd(call, args, root), root)
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
