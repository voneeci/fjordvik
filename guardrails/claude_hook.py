"""Claude Code PreToolUse hook: stop a tool call that would break GUARDRAILS.md.

Claude Code runs this before Bash, PowerShell, Monitor, terminal tool
(mcp__terminal__run_in_terminal), Read, Grep, Edit, Write, NotebookEdit, Artifact,
SendUserFile and the claude-artifacts tools that send local files (publish_files,
upload_asset) in this repository (see .claude/settings.json). It reads the call as
JSON on stdin. Exit code 2 blocks the call and shows the reason; exit code 0
lets it run, or asks Reece first when it prints an "ask" decision.

Rules it enforces (identifiers from GUARDRAILS.md):
  D2  no chat reads or writes the private banned-names list
  D3  no hand edits or shell writes to the generated data folders
  D8  no reading or sending a .env file (a search pattern on piped file names may name one)
  G1  commit named paths only
  G2  no hook bypass, no change to the hooks setting or to .git/hooks
  G3  no force push
  G9  ask Reece before any change to the guardrail files, including a git rollback
It catches the common forms of each breach, not every form: GUARDRAILS.md lists what it
doesn't catch, and the data tests, the fingerprints in GUARDRAILS.sha256 and the
permission rules in .claude/settings.json are the backstops. It fails closed: a call it
cannot read or check is blocked. The repository root comes from git (the repository
holding this file). Paths are compared in one canonical form (.. steps resolved, lower
case, prefixes, stream names, trailing dots and short names removed). Shell commands are
checked from the folder they run in, following cd, and wrapped commands (bash -c,
powershell -Command, eval and so on) are checked as commands too.

Maintained by Attena. Other chats suggest changes in guardrails/proposals/.
"""

import fnmatch
import json
import os
import posixpath
import re
import subprocess
import sys

GENERATED = ("data/tables/", "data/erp-extract/", "data/corpus/", "data/generator-truth/",
             "data/scenarios/")
GUARD_TESTS = tuple(f"{part}/tests/test_guardrails.py"
                    for part in ("data", "mcp", "powerbi", "power-automate", "service-ai"))
PROTECTED = ("guardrails.md", "guardrails.sha256", ".claude/settings.json",
             ".claude/settings.local.json") + GUARD_TESTS
PROTECTED_DIR, OPEN_DIR, GIT_HOOKS = "guardrails/", "guardrails/proposals/", ".git/hooks/"
CLAUDE_DIR = ".claude/"
# Cache folders and files: never generated data or guardrail files, so cleaning them is fine.
CACHES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
# Names that find -name patterns are tested against, to see what a filtered delete could hit.
GENERATED_SAMPLES = ("x.csv", "x.json", "x.md", "x.parquet", "x.txt", "manifest.json")
GUARD_SAMPLES = ("guardrails.md", "guardrails.sha256", "settings.json", "settings.local.json",
                 "check.py", "claude_hook.py", "shared_tests.py", "layout.md", "readme.md",
                 "claude.md", "pre-commit", ".gitattributes", "test_guardrails.py", "x.pdf", "x.txt")
# Environment variables whose names look like secrets (ANTHROPIC_API_KEY, GITHUB_TOKEN).
SECRET_PARTS = {"KEY", "APIKEY", "TOKEN", "SECRET", "PASSWORD", "PASSWD", "CREDENTIAL",
                "CREDENTIALS", "AUTH", "CONNECTION"}
SHELL_VARIABLE = re.compile(r"\$\{?(?:env:)?([A-Za-z_][A-Za-z0-9_]*)|%([A-Za-z_][A-Za-z0-9_]*)%")
CODE_VARIABLE = re.compile(r"(?i)(?:os\.environ\s*\[|os\.environ\.get\(|os\.getenv\(|environ\s*\[|"
                           r"GetEnvironmentVariable\()\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]")
# The whole environment: os.environ dumps, os.environ[k] read in a loop, PowerShell's env:
# drive (env:, Env:\, env:*), .NET and /proc/<id>/environ.
WHOLE_ENVIRONMENT = re.compile(r"(?i)(?<!env=)(?<!in )os\.environ\s*\)|os\.environ\.(?:items|values|copy)\(|"
                               r"os\.environ\s*\[\s*[A-Za-z_]\w*\s*\](?!\s*=(?!=))|"
                               r"GetEnvironmentVariables\(|\benv:\\?\s*\*?\s*['\"]?\s*(?:$|\||;)|"
                               r"\benv:\\?\*|/proc/[^/\s]+/environ")
_ENV_READ = (r"(?:\[(?:system\.)?environment\]::GetEnvironmentVariable\([^)]*\)"
             r"|\$\{?env:[A-Za-z_]\w*\}?)")
# A set check in expression form, at the start of a stage or inside brackets
# (echo $env:NAME -ne $null would print the key, so it doesn't count).
SET_CHECK = re.compile(rf"(?i)(^\s*|\(\s*)(?:\$null\s*-(?:ne|eq)\s*{_ENV_READ}|{_ENV_READ}\s*-(?:ne|eq)\s*\$null)")
SHELL_TOOLS = {"Bash", "PowerShell", "Monitor", "mcp__terminal__run_in_terminal"}
FILE_TOOLS = {"Read", "Grep", "Edit", "Write", "NotebookEdit"}
SEND_TOOLS = {"Artifact", "SendUserFile", "mcp__claude-artifacts__publish_files",
              "mcp__claude-artifacts__upload_asset"}
LONGEST = 20000
ENV_FILE = re.compile(r"(?i)(?<![\w-])\.env(\.(?!example\b)\w+)?(?![\w.-])")
ENV_NAMES = (".env", ".env.local")
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
                      r"|--no-ignore-removal|-[a-zA-Z]*[Au][a-zA-Z]*|\.|\./|\.\.|\.\./|\*|:/\S*)(\s|$)"),
     "stage named paths only (git add <path> ...), never -u, -A, --all, '.', '..', '*' or ':/'"),
    ("G1", re.compile(r"\bgit\s+commit\b.*\s(-[b-zA-Z]*a[a-zA-Z]*|--all?)(\s|$)"),
     "commit named paths only, never git commit -a"),
    ("G1", re.compile(r"\bgit\s+commit\b.*\s(\.|\./|\.\.|\.\./|\*|:/\S*)(\s|$)"),
     "commit named paths only, never '.', '..', '*' or ':/'"),
    ("G2", re.compile(r"\bgit\b.*\s--no-veri\w*"), "never bypass a git hook"),
    ("G2", re.compile(r"\bgit\s+commit\b.*\s-[a-mo-zA-Z]*n[a-zA-Z]*(\s|$)"),
     "never bypass a git hook (-n skips them)"),
    ("G3", re.compile(r"\bgit\s+push\b.*\s(--for\w*(-with-lease\S*)?|--force\S*|--mirror"
                      r"|-[a-zA-Z]*f[a-zA-Z]*|\+\S+)(\s|$)"), "never force push"),
]
MESSAGES = {
    "D2": "D2: only Reece reads or writes the private banned-names list",
    "D3": ("D3: the generated data folders change only through the generator "
           "(python -m fjordvik_data --out tables, from data/)"),
    "D8": "D8: never read, send or touch a .env file; read settings from environment variables",
    "D8env": ("D8: never print a key or the whole environment; to check a key is set, run "
              "python -c \"import os; print('NAME' in os.environ)\""),
    "G2": "G2: never change git hooks or their settings; only Reece does, by hand",
}
ASK_REASONS = {
    "G9": "GUARDRAILS.md G9: only Attena edits the guardrail files. Approve only in the Attena chat.",
    "wrapped": ("GUARDRAILS.md: the guardrail hook can't read this wrapped or very long command. "
                "Approve only if you know what it runs."),
}
# Words that come before the command itself (sudo rm, xargs rm, env X=1 rm).
PREFIXES = {"sudo", "xargs", "nohup", "time", "env", "command", "exec", "nice", "builtin",
            "&", ".", "call", "start"}
DELETERS = {"rm", "rmdir", "rd", "del", "erase", "remove-item", "ri", "unlink"}
# Commands that copy: only the destination is written.
COPIERS = {"cp", "copy", "copy-item", "cpi", "robocopy", "xcopy", "rsync", "install"}
# Commands that move or rename: the sources go (judged like a delete), the destination is written.
MOVERS = {"mv", "move", "move-item", "mi", "ren", "rename", "rename-item", "rni"}
RENAMERS = {"ren", "rename", "rename-item", "rni"}
# Commands that write every path they name.
WRITE_ALL = DELETERS | {"set-content", "sc", "add-content", "ac", "out-file", "clear-content",
                        "clc", "new-item", "ni", "mkdir", "md", "touch", "truncate", "tee",
                        "tee-object", "export-csv", "epcsv", "export-clixml", "ln", "patch", "dd"}
# Commands that write to the path given by an option, or to the current folder without one.
OPTION_WRITERS = {
    "curl": ({"-o", "--output"}, False), "wget": ({"-O", "--output-document", "-P",
                                                   "--directory-prefix"}, True),
    "invoke-webrequest": ({"-outfile"}, False), "iwr": ({"-outfile"}, False),
    "invoke-restmethod": ({"-outfile"}, False), "irm": ({"-outfile"}, False),
    "unzip": ({"-d"}, True), "expand-archive": ({"-destinationpath"}, True),
}
WRAP_SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
PYTHONS = {"python", "python3", "py"}
CODE_WRITES = re.compile(
    r"open\([^)]*?,\s*(?:mode\s*=\s*)?['\"][^'\"]*[wax+]|\.write_(?:text|bytes)\("
    r"|\.to_(?:csv|parquet|excel|json|pickle|feather)\(\s*[^)\s]|shutil\.|os\.(?:remove|unlink"
    r"|rename|replace|rmdir|removedirs)\(|\.(?:unlink|rename|replace|rmdir|touch)\(")
IO_WRITE = re.compile(r"(?i)\[(?:system\.)?io\.(?:file|directory)\]::"
                      r"(write|append|delete|copy|move|create|replace)")
GIT_PATH_WRITES = {"rm", "mv", "clean", "checkout", "restore"}
CD_WORDS = {"cd", "chdir", "set-location", "sl", "pushd", "push-location"}
REDIRECT = re.compile(r"(?:&>>?|>\||(?<![>&-])>>?)\s*(['\"]?)([^\s'\";|&]+)")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1([^\n]*)\n(.*?)\n\s*\2\s*(?=\n|$)", re.S)
NULL_TARGETS = {"/dev/null", "$null", "nul", "null"}
SEARCHERS = {"grep", "egrep", "rg", "findstr", "select-string", "sls"}
# Options that make a search read a file rather than its piped input.
FILE_OPTIONS = re.compile(r"(?<!\S)(-[A-Za-z]*f[A-Za-z]*|--file\S*)(?!\S)|(?i:/[gf]:)")
PS_FILE_OPTIONS = re.compile(r"(?i)(?<!\S)-(p(?!attern\b)\w*|l\w*|inputobject\b)")
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
    return rel in PROTECTED or rel.startswith(CLAUDE_DIR) or (
        rel.startswith(PROTECTED_DIR) and not rel.startswith(OPEN_DIR))


def secret_name(name: str) -> bool:
    """True when an environment variable's name looks like a key, token or password."""
    return name.upper() not in ("PWD", "OLDPWD") and bool(
        set(name.upper().split("_")) & SECRET_PARTS)


def prints_secrets(stage: str) -> bool:
    """True when a shell stage would print the whole environment or a secret-looking
    variable, or a stored token (gh auth token, git credential fill)."""
    words = [unquote(w) for w in stage.strip().lstrip("({").split()]
    if not words:
        return False
    name, args = name_of(words[0]), words[1:]
    if name in ("env", "printenv") and not [a for a in args if not a.startswith("-")
                                              and not re.match(r"^[A-Za-z_]\w*=", a)]:
        return True
    if name == "printenv" and any(secret_name(a) for a in args):
        return True
    if (name == "set" and not args) or (name == "export" and args[:1] in ([], ["-p"])) or \
            (name in ("declare", "typeset") and args[:1] in ([], ["-p"], ["-x"])):
        return True
    if name == "gh" and args[:2] == ["auth", "token"] or \
            name == "gh" and args[:2] == ["auth", "status"] and ("--show-token" in args or "-t" in args) or \
            name == "git" and args[:2] == ["credential", "fill"]:
        return True
    if WHOLE_ENVIRONMENT.search(stage):
        return True
    # Test-Path Env:\NAME and a comparison with $null only say whether a key is set, so
    # they may name one. A search may name a key in code it looks for (grep "getenv('NAME')").
    stage = SET_CHECK.sub(lambda m: m.group(1), stage)
    drive = [] if name == "test-path" else re.findall(r"(?i)\benv:\\?([A-Za-z_][A-Za-z0-9_]*)", stage)
    calls = [] if name in SEARCHERS else CODE_VARIABLE.findall(stage)
    return any(secret_name(a or b) for a, b in SHELL_VARIABLE.findall(stage)) or \
        any(secret_name(n) for n in drive + calls)


def code_prints_secrets(code: str) -> bool:
    """True when inline code reads a secret-looking variable or the whole environment.
    'NAME' in os.environ, the safe check, is allowed."""
    return bool(WHOLE_ENVIRONMENT.search(code)) or any(
        secret_name(n) for n in CODE_VARIABLE.findall(code))


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


def unquote(word: str) -> str:
    return word[1:-1] if len(word) > 1 and word[0] == word[-1] and word[0] in "'\"" else word


def name_of(word: str) -> str:
    """A command word's name: no quotes, folder or .exe, in lower case."""
    name = unquote(word).replace("\\", "/").rsplit("/", 1)[-1].lower()
    return name[:-4] if name.endswith(".exe") else name


def blank_quotes(stage: str, spans: list[tuple[int, int]]) -> str:
    """The stage with the text inside quotes removed, so messages aren't read as options."""
    for a, b in sorted(spans, reverse=True):
        stage = stage[:a] + "''" + stage[b:]
    return stage


def git_normal(text: str) -> str:
    """git commands with their global options dropped, and git.exe or & git read as git."""
    text = re.sub(r"(?i)(^|\s)&\s+(?=git\b)", r"\1", text)
    text = re.sub(r"(?i)\bgit\.exe\b", "git", text)
    return GIT_GLOBAL.sub("git", text)


def env_glob(word: str) -> bool:
    """True when a wildcard word could match a .env file: its letters all come from .env
    (*env, ?env, .e*, *nv). Quotes don't stop PowerShell expanding it."""
    base = unquote(word).replace("\\", "/").rstrip(";)").rsplit("/", 1)[-1].lower()
    if not re.search(r"[*?\[]", base) or len(re.sub(r"[*?\[\]]", "", base)) < 2:
        return False
    return any(fnmatch.fnmatchcase(n, base) for n in ENV_NAMES)


def banned_glob(word: str) -> bool:
    """True when a wildcard word starting with three letters would match the private list."""
    base = unquote(word).replace("\\", "/").rstrip(";)").rsplit("/", 1)[-1].lower()
    if not re.search(r"[*?\[]", base) or not re.match(r"^[^*?\[]{3}", base):
        return False
    return any(fnmatch.fnmatchcase(n, base) for n in BANNED_NAMES)


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
    word = unquote(word).replace("\\", "/")
    if "=" in word and not word.startswith("="):
        word = word.split("=", 1)[1]
    if word == "~" or word.startswith("~/"):
        word = os.path.expanduser(word).replace("\\", "/")
    if not word or word[0] in "-$~&%@" or word.lower() in NULL_TARGETS or "://" in word:
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


def judge(segments: list[str], deleting: bool, generated: bool = True) -> str | None:
    """D3 (generated data), G2 (git hooks), G9 (guardrail files) or None for one path a
    command writes, moves or deletes. git's own path commands skip the generated folders
    (G7 allows restoring them) and .git/hooks (git never writes it). Cache folders and
    files never count."""
    if any(s in CACHES for s in segments) or (segments and segments[-1].endswith(".pyc")):
        return None
    if generated:
        for g in GENERATED:
            where = place(segments, g)
            if where == "in" or (where == "above" and deleting):
                return "D3"
        where = place(segments, GIT_HOOKS)
        if where == "in" or (where == "above" and deleting):
            return "G2"
    in_open = place(segments, OPEN_DIR) == "in"
    for p in PROTECTED + (PROTECTED_DIR, CLAUDE_DIR):
        where = place(segments, p)
        if (where == "in" and not in_open) or (where == "above" and deleting):
            return "G9"
    return None


def worst(codes: list[str | None]) -> str | None:
    """The strongest verdict: a block (D8env, D3, G2) before an ask (G9, wrapped)."""
    for code in ("D8env", "D3", "G2", "G9", "wrapped"):
        if code in codes:
            return code
    return None


def check_paths(words: list[tuple[str, bool]], cwd: str, root: str, generated: bool = True) -> str | None:
    codes = []
    for word, deleting in words:
        path = as_path(word, cwd)
        segments = in_repo(path, root) if path else None
        if segments is not None:
            codes.append(judge(segments, deleting, generated))
    return worst(codes)


def option_value(args: list[str], names: set[str]) -> list[str]:
    """Values given to any of the named options (-o x, --output=x), names matched exactly
    for single-letter options and without case for the rest."""
    found = []
    for i, arg in enumerate(args):
        bare = unquote(arg)
        for name in names:
            same = bare == name if len(name) == 2 else bare.lower() == name.lower()
            if same and i + 1 < len(args):
                found.append(args[i + 1])
            elif len(name) > 2 and bare.lower().startswith(name.lower() + "="):
                found.append(bare.split("=", 1)[1])
    return found


def positional(args: list[str]) -> list[str]:
    return [a for a in args if not unquote(a).startswith("-")]


def rolls_back(revs: list[str], root: str, commits: bool = False) -> bool:
    """True when moving to a revision (or reverting commits) would change a guardrail
    file, or git can't say."""
    paths = ["GUARDRAILS.md", "GUARDRAILS.sha256", "guardrails", ".claude", *GUARD_TESTS]
    for rev in revs:
        command = (["git", "-C", root, "diff-tree", "--no-commit-id", "--name-only", "-r", rev]
                   if commits else ["git", "-C", root, "diff", "--name-only", rev])
        try:
            result = subprocess.run(command + ["--", *paths], capture_output=True, text=True,
                                    timeout=3)
        except (OSError, subprocess.SubprocessError):
            return True
        if result.returncode != 0:
            return True
        if any(line and not line.startswith(OPEN_DIR) for line in result.stdout.splitlines()):
            return True
    return False


def git_verdict(stage: str, cwd: str, root: str) -> str | None:
    """D3, G9 or None for a git stage that writes files: rm, mv, clean, checkout, restore,
    reset and revert."""
    inside = re.match(r"(?i)\S+\s+-C\s+(['\"]?)(\S+?)\1(\s|$)", stage)
    cwd = (as_path(inside.group(2), cwd) or cwd) if inside else cwd
    words = [m.group(0) for m in TOKEN.finditer(git_normal(stage))]
    if len(words) < 2:
        return None
    sub, args = words[1].lower(), words[2:]
    if sub == "restore" and any(a in ("--staged", "-S") for a in args) and \
            not any(a in ("--worktree", "-W") for a in args):
        return None
    if sub == "checkout" and any(a in ("-b", "-B", "--orphan") for a in args):
        return None
    if sub in GIT_PATH_WRITES:
        after = args[args.index("--") + 1:] if "--" in args else None
        paths = after if after is not None else positional(args)
        rev = None
        if sub == "checkout" and after is not None:
            before = positional(args[:args.index("--")])
            rev = before[0] if before else None
        if sub == "checkout" and after is None:
            exists = [p for p in paths if unquote(p) in (".", ":/") or
                      (as_path(p, cwd) and os.path.exists(as_path(p, cwd)))]
            if not exists:
                return "G9" if paths and rolls_back(paths[:1], root) else None
            rev = next((p for p in paths if p not in exists), None)
            paths = exists
        if sub == "restore":
            rev = (option_value(args, {"-s", "--source"}) or [None])[0]
            paths = [p for p in paths if p != rev]
        # G7 allows restoring generated files from HEAD only: an older revision changes
        # the data without the generator (D3).
        if rev and unquote(rev).upper() not in ("HEAD", "@"):
            for p in ["." if unquote(p) in (":/", ":/*") else p for p in paths]:
                path = as_path(p, cwd)
                segments = in_repo(path, root) if path else None
                if segments is not None and any(place(segments, g) for g in GENERATED):
                    return "D3"
        if sub == "clean":
            if any(re.fullmatch(r"-\w*n\w*|--dry-run", a) for a in args):
                return None
            paths = paths or ["."]
        if sub == "mv":
            paths = paths[:-1]
        whole = ["." if unquote(p) in (":/", ":/*") else p for p in paths]
        return check_paths([(p, True) for p in whole], cwd, root,
                           generated=sub in {"rm", "mv", "clean"})
    if sub == "reset" and any(a in ("--hard", "--keep", "--merge") for a in args):
        revs = [a for a in positional(args) if a != "--"][:1]
        return "G9" if revs and unquote(revs[0]).upper() not in ("HEAD", "@") and rolls_back(revs, root) else None
    if sub == "revert":
        revs = positional(args)
        return "G9" if revs and rolls_back(revs, root, commits=True) else None
    if sub == "switch":
        revs = positional(args)
        creating = any(a in ("-c", "-C", "--create") for a in args)
        return "G9" if revs and not creating and rolls_back(revs[:1], root) else None
    return None


WRITE_CALL = re.compile(
    r"(?i)(?<![\w.])open\(|\.open\(|\.to_(?:csv|parquet|excel|json|pickle|feather|html|xml|hdf|stata)\("
    r"|shutil\.(?:copy\w*|move|rmtree)\(|os\.(?:remove|unlink|rmdir|removedirs|rename|replace"
    r"|makedirs|mkdir)\(|\.(?:write_text|write_bytes|unlink|rename|replace|rmdir|touch|mkdir)\("
    r"|\[(?:system\.)?io\.(?:file|directory)\]::(?:write|append|delete|copy|move|create|replace)\w*\(")
LITERAL = re.compile(r"[rRbBuU]?(['\"])(.*?)\1")


def call_args(code: str, start: int) -> list[str]:
    """The top-level arguments of the call whose opening bracket is at start."""
    args, depth, quote, begin = [], 0, "", start + 1
    for i in range(start, len(code)):
        ch = code[i]
        if quote:
            quote = "" if ch == quote else quote
        elif ch in "'\"":
            quote = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                args.append(code[begin:i])
                return [a.strip() for a in args if a.strip()]
        elif ch == "," and depth == 1:
            args.append(code[begin:i])
            begin = i + 1
    return [a.strip() for a in args if a.strip()]


def receiver(code: str, end: int) -> str:
    """The expression a method is called on: Path('x') in Path('x').write_text(...)."""
    i, depth = end, 0
    while i > 0:
        ch = code[i - 1]
        if ch in ")]":
            depth += 1
        elif ch in "([":
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and not (ch.isalnum() or ch in "_."):
            break
        i -= 1
    return code[i:end]


def write_targets(code: str) -> list[tuple[str, bool]]:
    """(target expression, deleting) for each file a piece of Python or PowerShell code
    writes, moves or deletes. Paths it only reads are left out."""
    found = []
    for m in WRITE_CALL.finditer(code):
        call, args = m.group(0).lower(), call_args(code, m.end() - 1)
        positional_args = [a for a in args if not re.match(r"^\w+\s*=", a)]
        named = {k: v.strip() for k, v in (re.match(r"^(\w+)\s*=(.*)$", a, re.S).groups()
                                           for a in args if re.match(r"^\w+\s*=", a))}
        # A path given by keyword: open(file=...), to_csv(path_or_buf=...).
        positional_args = positional_args or [named[k] for k in ("file", "path_or_buf", "path")
                                              if k in named][:1]
        if call == "open(":
            mode = named.get("mode", positional_args[1] if len(positional_args) > 1 else "'r'")
            if positional_args and re.search(r"[wax+]", unquote(mode.strip())):
                found.append((positional_args[0], False))
        elif call == ".open(":
            # Path(...).open('w') writes its receiver; tarfile.open(name, 'w') its first argument.
            first = unquote(positional_args[0]) if positional_args else ""
            mode = named.get("mode", "'r'")
            if re.fullmatch(r"[rwaxbt+]+", first):
                mode = positional_args[0]
                if re.search(r"[wax+]", unquote(mode.strip())):
                    found.append((receiver(code, m.start()), False))
            elif positional_args and re.search(r"[wax+]", unquote(
                    (positional_args[1] if len(positional_args) > 1 else mode).strip())):
                found.append((positional_args[0], False))
            elif re.search(r"[wax+]", unquote(mode.strip())):
                found.append((receiver(code, m.start()), False))
        elif call.startswith(".to_"):
            found += [(positional_args[0], False)] if positional_args else []
        elif call.startswith("shutil.copy"):
            found += [(positional_args[1], False)] if len(positional_args) > 1 else []
        elif call == "shutil.move(":
            found += [(a, i == 0) for i, a in enumerate(positional_args[:2])]
        elif call.startswith(("shutil.rmtree", "os.")):
            found += [(a, True) for a in positional_args[:2 if "rename" in call or "replace" in call else 1]]
        elif call.startswith("["):
            found += [(positional_args[0], "delete" in call)] if positional_args else []
        else:
            target = receiver(code, m.start())
            # str.replace and DataFrame.rename are common; only a Path(...) receiver is a file.
            if call not in (".replace(", ".rename(") or "Path(" in target:
                found.append((target, call in (".unlink(", ".rmdir(")))
    return found


def replace_name(text: str, name: str, value: str) -> str:
    """text with each use of the name (outside quotes, not an attribute or a call) replaced
    by (value)."""
    blanked = LITERAL.sub(lambda m: " " * len(m.group(0)), text)
    spans = [m.span() for m in re.finditer(rf"(?<![\w.]){re.escape(name)}(?!\w)(?!\s*\()", blanked)]
    for a, b in reversed(spans):
        text = text[:a] + f"({value})" + text[b:]
    return text


def expand(expression: str, code: str, depth: int = 0) -> list[str]:
    """The forms a write target can take, with each name assigned in the code (at the start
    of a line or after ;) replaced by its value, up to three levels: TABLES / 'x.csv' with
    TABLES = Path('data') / 'tables' becomes (Path('data') / 'tables') / 'x.csv'."""
    if depth >= 3:
        return [expression]
    blanked = LITERAL.sub(lambda m: " " * len(m.group(0)), expression)
    names = dict.fromkeys(re.findall(r"(?<![\w.])([A-Za-z_]\w*)(?!\w)(?!\s*\()", blanked))
    forms = [expression]
    for name in names:
        values = re.findall(rf"(?m)(?:^|;)\s*{re.escape(name)}\s*(?::[^=\n]+)?=(?!=)\s*([^;\n]+)", code)
        values = [v.strip() for v in values if v.strip() != name][:4]
        if values:
            forms = [replace_name(f, name, v) for f in forms for v in values][:8]
    if forms == [expression]:
        return forms
    return [g for f in forms for g in expand(f, code, depth + 1)][:8]


def code_verdict(code: str, cwd: str, root: str, writes: bool = False) -> str | None:
    """D3, G9 or None for code that writes files. Each write target is judged: a quoted
    path as written, a path built from quoted parts (Path('data') / 'tables', os.path.join,
    an f-string) by joining the parts. A target held in a variable counts as generated data
    or a guardrail file when the code names one (a quoted 'tables', 'guardrails' and so on),
    or when the code runs inside one."""
    targets = write_targets(code)
    if not targets and not (writes or CODE_WRITES.search(code)):
        return None
    here = in_repo(cwd, root)
    codes = []
    for expression, deleting in targets:
        for text in expand(expression.strip(), code):
            parts = [re.sub(r"\{[^}]*\}", "", lit).strip("/\\") for _, lit in LITERAL.findall(text)]
            parts = [p for p in parts if p]
            if parts:
                base = root if re.search(r"f['\"]\{|\bROOT\b|parents\[", text) else cwd
                path = as_path("/".join(parts), base)
                segments = in_repo(path, root) if path else None
                codes.append(judge(segments, deleting) if segments is not None else None)
            elif here is not None:
                codes.append(judge(here, False))  # unknown target: counts only inside a protected folder
    if not targets and here is not None:
        codes.append(judge(here, False))
    return worst(codes)


def inner_command(words: list[str], i: int) -> str | None:
    """The command a wrapper runs (bash -c, cmd /c, powershell -Command, eval, iex), ""
    when it can't be read (an encoded command), or None when this isn't a wrapper."""
    name, args = name_of(words[i]), words[i + 1:]
    if name in WRAP_SHELLS:
        for j, arg in enumerate(args):
            if re.fullmatch(r"-\w*c", arg):
                return unquote(args[j + 1]) if j + 1 < len(args) else ""
        return None
    if name == "cmd":
        for j, arg in enumerate(args):
            if arg.lower() in ("/c", "/k"):
                return unquote(" ".join(args[j + 1:]))
        return None
    if name in {"powershell", "pwsh"}:
        for j, arg in enumerate(args):
            low = arg.lower()
            if re.fullmatch(r"-e(c|n|nc|nco\w*)?|-encodedcommand", low):
                return ""
            if re.fullmatch(r"-c(o(m(m(a(n(d)?)?)?)?)?)?", low):
                return unquote(" ".join(args[j + 1:]))
            if low.startswith("-f"):
                return None
        rest = positional(args)
        return unquote(" ".join(rest)) if rest else None
    if name == "eval" or name in {"iex", "invoke-expression"}:
        rest = [a for a in args if a.lower() != "-command"]
        return unquote(" ".join(rest))
    return None


def find_parts(args: list[str]) -> tuple[list[str], list[str]]:
    """A find command's start folders and its -name, -iname, -path and -ipath patterns."""
    start = [a for a in args[:next((k for k, a in enumerate(args) if a.startswith("-")),
                                   len(args))]] or ["."]
    return start, option_value(args, {"-name", "-iname", "-path", "-ipath"})


def filtered_delete(starts: list[str], filters: list[str], cwd: str, root: str) -> str | None:
    """D3, G9 or None for deleting what name filters match under the start folders
    (find -name ... -delete, Get-ChildItem -Filter ... | Remove-Item). A filter naming a
    cache folder or file only cleans caches; without a filter, the folders themselves go."""
    def cache(f: str) -> bool:
        bare = unquote(f).lower()
        return any(p in CACHES for p in re.split(r"[/\\]", bare)) or bare.endswith((".pyc", ".py[co]"))

    if filters and all(cache(f) for f in filters):
        return None
    names = [unquote(f).lower().rsplit("/", 1)[-1] for f in filters if not cache(f)]
    if not names:
        return check_paths([(s, True) for s in starts], cwd, root)
    # A filtered delete only removes what the filter matches: judge it by whether the
    # pattern could match a generated file or a guardrail file's name.
    hits_data = any(fnmatch.fnmatchcase(n, f) for f in names for n in GENERATED_SAMPLES)
    hits_guard = any(fnmatch.fnmatchcase(n, f) for f in names for n in GUARD_SAMPLES)
    codes = []
    for s in starts:
        path = as_path(s, cwd)
        segments = in_repo(path, root) if path else None
        if segments is None:
            continue
        if hits_data and any(place(segments, g) for g in GENERATED):
            codes.append("D3")
        if hits_guard and any(place(segments, p) for p in PROTECTED + (PROTECTED_DIR, CLAUDE_DIR)):
            codes.append("G9")
    return worst(codes)


LISTERS = {"get-childitem", "gci", "ls", "dir"}


def piped_delete(before: list[tuple[str, list[tuple[int, int]]]], cwd: str, root: str) -> str | None:
    """D3, G9 or None for a delete fed by the stages before it: find's folders and filters,
    Get-ChildItem's paths and -Filter or -Include, or any other command's path arguments
    (git ls-files data/tables | xargs rm)."""
    codes = []
    for stage, _ in before:
        words = [m.group(0) for m in TOKEN.finditer(stage.strip())]
        if not words:
            continue
        name, args = name_of(words[0]), words[1:]
        if name == "find":
            codes.append(filtered_delete(*find_parts(args), cwd, root))
        elif name in LISTERS:
            filters = option_value(args, {"-filter", "-include"})
            skip = set(filters + option_value(args, {"-exclude", "-depth"}))
            paths = [p for p in positional(args) if p not in skip] or ["."]
            codes.append(filtered_delete(paths, filters, cwd, root))
        else:
            codes.append(check_paths([(p, True) for p in positional(args)], cwd, root))
    return worst(codes)


def stage_verdict(stage: str, spans: list[tuple[int, int]], cwd: str, root: str,
                  bodies: list[str], depth: int, before: list | None = None) -> str | None:
    """D3, G2, G9, wrapped or None for one pipe stage run in the folder cwd."""
    # A > inside quotes is text, not a redirect; a quoted target after a real > still counts.
    redirects = [m.group(2) for m in REDIRECT.finditer(stage)
                 if not any(a <= m.start() < b for a, b in spans)]
    stage = stage.strip()
    if stage[:1] in "({":  # a subshell or brace group: (cd x && rm y) or { cd x; rm y; }
        stage = stage.lstrip("({").strip()
    if stage.endswith(("}", ")")) and not stage.endswith("{}") and \
            stage.count("(") < stage.count(")") + (stage[-1] == "}"):
        stage = stage.rstrip(")}").strip()
    words = [m.group(0) for m in TOKEN.finditer(stage)]
    i = 0
    while i < len(words) and (name_of(words[i]) in PREFIXES or re.match(r"^[A-Za-z_]\w*=", words[i])
                              or (i > 0 and words[i].startswith("-")
                                  and name_of(words[i - 1]) in PREFIXES)):
        i += 1
    if i >= len(words):
        return None
    name, args = name_of(words[i]), words[i + 1:]
    codes = [check_paths([(r, False) for r in redirects], cwd, root)]
    if name == "git":
        codes.append(git_verdict(" ".join(words[i:]), cwd, root))
        return worst(codes)
    inner = inner_command(words, i)
    if inner is not None:
        if not inner.strip() or depth > 2:
            return worst(codes + ["wrapped"])
        found = shell_verdict(inner, cwd, root, depth + 1)
        if found and not found.startswith("ask:"):
            return found  # a block from the inner command, with its own reason
        return worst(codes + ([found[4:]] if found else []))
    if name in PYTHONS:
        flags = [a for a in args if re.fullmatch(r"-\w*c", a)]
        if flags:
            j = args.index(flags[0])
            code = unquote(args[j + 1]) if j + 1 < len(args) else ""
            if code_prints_secrets(code):
                return "D8env"
            codes.append(code_verdict(code, cwd, root))
        for marker in re.findall(r"__heredoc_(\d+)__", stage):
            if code_prints_secrets(bodies[int(marker)]):
                return "D8env"
            codes.append(code_verdict(bodies[int(marker)], cwd, root))
        # A script file: read it and check its writes (python -m <module> isn't read, so
        # the data generator runs as usual).
        script = next((a for a in args if not a.startswith("-")), None) if not flags and \
            not any(a == "-m" for a in args) else None
        path = as_path(script, cwd) if script and unquote(script).lower().endswith(".py") else None
        if path and os.path.isfile(path) and os.path.getsize(path) <= 200_000:
            with open(path, encoding="utf-8", errors="replace") as handle:
                codes.append(code_verdict(handle.read(), cwd, root))
        return worst(codes)
    if IO_WRITE.search(stage):
        codes.append(code_verdict(stage, cwd, root, writes=True))
    pos = positional(args)
    if name in COPIERS:
        dest = option_value(args, {"-destination", "-dest", "-target", "-t", "--target-directory"})
        dest = dest or (pos[1:2] if name == "robocopy" else pos[-1:])
        codes.append(check_paths([(d, False) for d in dest], cwd, root))
        if name == "robocopy" and any(a.lower() in ("/mov", "/move") for a in args):
            codes.append(check_paths([(s, True) for s in pos[:1]], cwd, root))
        # Copying a folder named like a generated one into its parent (cp -r x/tables data/)
        names = {g.rstrip("/").rsplit("/", 1)[-1] for g in GENERATED}
        if any(name_of(s).rstrip("/") in names for s in pos if s not in dest):
            codes.append(check_paths([(posixpath.join(unquote(d).replace("\\", "/"), n), False)
                                      for d in dest for n in names], cwd, root))
    elif name in MOVERS:
        dest = option_value(args, {"-destination", "-dest", "-t", "--target-directory"})
        sources = [p for p in pos if p not in dest]
        if not dest and name not in RENAMERS and len(sources) > 1:
            dest = sources[-1:]
            sources = sources[:-1]
        elif name in RENAMERS:
            sources, dest = sources[:1], []
        codes.append(check_paths([(s, True) for s in sources] + [(d, False) for d in dest],
                                 cwd, root))
    elif name in WRITE_ALL or (name in {"sed", "perl"} and any(
            re.fullmatch(r"-\w*i\S*|--in-place\S*", unquote(a)) for a in args)):
        codes.append(check_paths([(p, name in DELETERS) for p in pos], cwd, root))
        # A delete with no path of its own (... | Remove-Item, ... | xargs rm, $_ or {})
        # deletes what the stages before it list.
        if name in DELETERS and before and all(unquote(p) == "{}" or unquote(p).startswith("$")
                                               for p in pos):
            codes.append(piped_delete(before, cwd, root))
    elif name == "find" and ("-delete" in args or "-exec" in args):
        codes.append(filtered_delete(*find_parts(args), cwd, root))
    elif name == "tar":
        flags = "".join(a.lstrip("-") for a in args if re.fullmatch(r"-?[a-zA-Z]+", a) and
                        (a.startswith("-") or args.index(a) == 0))
        targets = []
        if "x" in flags or "--extract" in args or "--get" in args:
            targets += option_value(args, {"-C", "--directory"}) or ["."]
        if "c" in flags or "--create" in args:
            targets += [args[k + 1] for k, a in enumerate(args[:-1])
                        if re.fullmatch(r"-?[a-zA-Z]*f", a) or a == "--file"]
        codes.append(check_paths([(t, False) for t in targets], cwd, root))
    elif name in OPTION_WRITERS:
        options, to_folder = OPTION_WRITERS[name]
        targets = option_value(args, options)
        if name == "expand-archive" and not targets and len(pos) > 1:
            targets = pos[1:2]
        codes.append(check_paths([(t, False) for t in targets or (["."] if to_folder else [])],
                                 cwd, root))
    return worst(codes)


def step_into(cwd: str, stage: str) -> str:
    """The folder after a cd, Set-Location or pushd stage; unchanged otherwise."""
    words = [unquote(w) for w in stage.strip().lstrip("({").split()]
    if not words or words[0].lower() not in CD_WORDS:
        return cwd
    args = [w for w in words[1:] if not w.startswith("-")]
    if not args:
        return cwd
    path = as_path(args[0].rstrip(")};"), cwd)
    return path if path else cwd


def shell_verdict(command: str, cwd: str, root: str, depth: int = 0) -> str | None:
    """A rule code (D2, D3, D8, G1, G2, G3, G9, wrapped) with its reason, or None, for a
    shell command run in cwd. Blocks come back as "D3: ...", asks as "ask:G9"."""
    if len(command) > LONGEST:
        return "ask:wrapped"
    command = re.sub(r"\\\r?\n", " ", command)  # a line continuation joins two lines
    if HOOKS_SETTING.search(command):
        return MESSAGES["G2"]
    bodies: list[str] = []

    def keep(m: re.Match) -> str:
        bodies.append(m.group(4))
        return f"<<{m.group(2)} __heredoc_{len(bodies) - 1}__{m.group(3)}"

    command = HEREDOC.sub(keep, command)
    ask = None
    for stages in split_command(command):
        for index, (stage, spans) in enumerate(stages):
            lead = [w for w in stage.strip().lstrip("({").split() if w != "&"][:1]
            git = bool(lead) and name_of(lead[0]) == "git"
            seen = blank_quotes(stage, spans) if git else stage
            words = [m.group(0) for m in TOKEN.finditer(seen)]
            if (ENV_FILE.search(seen) and not safe_env_search(stage, spans, index)) or \
                    any(env_glob(w) for w in words):
                return MESSAGES["D8"]
            if any(banned_glob(w) for w in words):
                return MESSAGES["D2"]
            if prints_secrets(seen):
                return MESSAGES["D8env"]
            if git:
                flat = git_normal(seen)
                for rule, pattern, why in GIT_RULES:
                    if pattern.search(flat):
                        return f"{rule}: {why}"
            for marker in re.findall(r"__heredoc_(\d+)__", stage):
                body = bodies[int(marker)]
                if name_of(stage.split()[0]) in PYTHONS and ENV_FILE.search(body):
                    return MESSAGES["D8"]
            code = stage_verdict(stage, spans, cwd, root, bodies, depth, stages[:index])
            if code in ("D3", "G2", "D8env"):
                return MESSAGES[code]
            if code and ":" in code:
                return code  # a block message from a wrapped command
            ask = ask or code
            if index == 0:
                cwd = step_into(cwd, stage)
    return f"ask:{ask}" if ask else None


def shell_cwd(call: dict, args: dict, root: str) -> str:
    """The folder a shell command runs in: the call's own, or for the terminal tool its
    cwd argument (absolute, ~ or relative to the call's folder)."""
    cwd = call.get("cwd") or root
    if call.get("tool_name") == "mcp__terminal__run_in_terminal" and args.get("cwd"):
        cwd = os.path.join(cwd, os.path.expanduser(args["cwd"]))
    return cwd


def sent_paths(args: dict) -> list[str]:
    """Every local file path a publishing or sending tool (SEND_TOOLS) would send."""
    found = [args.get("file_path"), args.get("root")] + list(args.get("file_paths") or [])
    files = args.get("files") or []
    for item in files.values() if isinstance(files, dict) else files:
        if isinstance(item, dict):
            found += [item.get("from"), item.get("path")]
        else:
            found.append(item)
    return [p for p in found if isinstance(p, str) and p]


def reason(call: dict, root: str) -> str | None:
    """None to allow, "ask:<why>" to ask Reece, or the reason to block."""
    tool, args = call.get("tool_name", ""), call.get("tool_input") or {}
    cwd = call.get("cwd") or root
    raw = args.get("file_path") or args.get("notebook_path") or args.get("path") or ""
    raws = sent_paths(args) if tool in SEND_TOOLS else ([raw] if raw else [])
    paths = [canonical(r, cwd) for r in raws]
    command = (args.get("command") or "") if tool in SHELL_TOOLS else ""
    pattern = (args.get("glob") or "") if tool == "Grep" else ""
    if any(BANNED_LIST.search(p) for p in raws + paths) or BANNED_LIST.search(command) \
            or BANNED_LIST.search(pattern) or banned_glob(pattern):
        return MESSAGES["D2"]
    if tool in FILE_TOOLS | SEND_TOOLS and (any(is_env_file(p) for p in paths)
                                           or ENV_FILE.search(pattern) or env_glob(pattern)):
        return MESSAGES["D8"]
    if tool in {"Edit", "Write", "NotebookEdit"} and paths:
        rel = relative(paths[0], root)
        if rel.startswith(GENERATED):
            return (f"D3: {rel} is generated; change data/src/fjordvik_data and run "
                    "python -m fjordvik_data --out tables from data/ instead")
        if rel.startswith(GIT_HOOKS):
            return MESSAGES["G2"]
        if is_protected(rel):
            return "ask:G9"
    if command:
        return shell_verdict(command, shell_cwd(call, args, root), root)
    return None


def main() -> int:
    try:
        call = json.load(sys.stdin)
        why = reason(call, repo_root())
    except Exception as error:  # fail closed: a call the hook can't check doesn't run
        print(f"Blocked by GUARDRAILS.md: the guardrail hook could not check this call "
              f"({type(error).__name__}).", file=sys.stderr)
        return 2
    if why and why.startswith("ask:"):
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": ASK_REASONS.get(why[4:], ASK_REASONS["G9"])}}))
        return 0
    if why:
        print(f"Blocked by GUARDRAILS.md {why}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
