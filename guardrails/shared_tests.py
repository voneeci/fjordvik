"""Guardrail tests every part runs. Each part's tests/test_guardrails.py imports these,
so a breach of GUARDRAILS.md fails every part's test run, not just one.

Maintained by Attena (see GUARDRAILS.md).
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import check

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "guardrails" / "claude_hook.py"


def test_repository_has_no_guardrail_findings():
    assert check.check(ROOT) == []


def test_guardrails_file_matches_its_fingerprint():
    recorded = (ROOT / "GUARDRAILS.sha256").read_text(encoding="utf-8").split()[0]
    assert recorded == hashlib.sha256((ROOT / "GUARDRAILS.md").read_bytes()).hexdigest()


def test_checker_catches_each_planted_breach(tmp_path):
    """A throwaway repository with one breach per rule the checker covers. Secrets are
    joined from parts so this file holds none itself."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "GUARDRAILS.md").write_text("rules\n", encoding="utf-8")
    (tmp_path / "GUARDRAILS.sha256").write_text("0" * 64 + "  GUARDRAILS.md\n", encoding="utf-8")
    (tmp_path / "dash.md").write_text("A sentence " + chr(0x2014) + " with a dash.\n", encoding="utf-8")
    (tmp_path / "quoted.md").write_text('As published: "data visualization" stays.\n', encoding="utf-8")
    (tmp_path / "spelling.md").write_text("We analyze the color of things.\n", encoding="utf-8")
    (tmp_path / "count.md").write_text("Fjordvik is five projects.\n", encoding="utf-8")
    (tmp_path / "key.py").write_text("KEY = 'sk-ant-" + "x" * 24 + "'\n", encoding="utf-8")
    (tmp_path / "otherkey.py").write_text("KEY = 'sk-" + "y" * 24 + "'\n", encoding="utf-8")
    (tmp_path / "conn.txt").write_text("Server=db1;User ID=app;" + "Pass" + "word=hunter22;\n",
                                       encoding="utf-8")
    (tmp_path / "url.md").write_text("postgresql://app:" + "hunter22" + "@db1/fjordvik\n",
                                     encoding="utf-8")
    (tmp_path / "azure.txt").write_text("Account" + "Key=" + "A" * 40 + "==\n", encoding="utf-8")
    (tmp_path / "placeholder.md").write_text("postgresql://app:${PASSWORD}@db1/fjordvik\n",
                                             encoding="utf-8")
    (tmp_path / ".env").write_text("NAME=value\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("NAME=\n", encoding="utf-8")
    # L1 and L4: a layout map, a stray folder and an evidence file with no run date
    (tmp_path / "guardrails").mkdir()
    (tmp_path / "guardrails" / "layout.md").write_text(
        "Parts: part\n\n- `*.md`: x\n- `*.py`: x\n- `*.txt`: x\n- `GUARDRAILS.sha256`: x\n"
        "- `.env.example`: x\n- `guardrails/*`: x\n- `<part>/evidence/*`: x\n", encoding="utf-8")
    (tmp_path / "scratch").mkdir()
    (tmp_path / "scratch" / "notes.md").write_text("notes\n", encoding="utf-8")
    (tmp_path / "part" / "evidence").mkdir(parents=True)
    (tmp_path / "part" / "evidence" / "run.txt").write_text("1 passed\n", encoding="utf-8")
    (tmp_path / "part" / "evidence" / "pytest-x-2026-11-02.txt").write_text("1 passed\n",
                                                                            encoding="utf-8")
    found = "\n".join(check.check(tmp_path))
    assert "GUARDRAILS.md: changed without updating" in found
    assert "W1 dash.md" in found
    assert "W2 spelling.md: American spelling 'analyze'" in found
    assert "W2 spelling.md: American spelling 'color'" in found
    assert "W5 count.md" in found
    for name in ("key.py", "otherkey.py", "conn.txt", "url.md", "azure.txt"):
        assert f"D8 {name}" in found, name
    assert "D8 .env:" in found or "D8 .env: a .env file" in found
    assert "quoted.md" not in found and ".env.example" not in found
    assert "placeholder.md" not in found
    assert "L1 scratch/: 1 file(s) not on the layout map" in found
    assert "L4 part/evidence/run.txt" in found
    assert "pytest-x-2026-11-02.txt" not in found and "L1 (root)" not in found


def run_hook(call: dict | str, project: Path | None = None) -> str:
    """The hook's decision on one tool call: "block", "ask" or "allow". A project folder,
    when given, is the chat's project folder and the call's working folder."""
    if project is not None:
        call = {**call, "cwd": str(project)}
    result = subprocess.run([sys.executable, str(HOOK)],
                            input=call if isinstance(call, str) else json.dumps(call),
                            text=True, capture_output=True,
                            env={"CLAUDE_PROJECT_DIR": str(project or ROOT),
                                 "SYSTEMROOT": "C:\\Windows", "PATH": os.environ.get("PATH", "")})
    if result.returncode == 2:
        return "block"
    if result.returncode == 0 and '"permissionDecision": "ask"' in result.stdout:
        return "ask"
    return "allow" if result.returncode == 0 else f"exit {result.returncode}"


def bash(command: str, cwd: Path = ROOT) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}


def powershell(command: str) -> dict:
    return {"tool_name": "PowerShell", "tool_input": {"command": command}, "cwd": str(ROOT)}


def monitor(command: str | None = None, ws: str | None = None) -> dict:
    args = {"description": "x", "timeout_ms": 1000}
    if command is not None:
        args["command"] = command
    if ws is not None:
        args["ws"] = {"url": ws}
    return {"tool_name": "Monitor", "tool_input": args, "cwd": str(ROOT)}


def terminal(command: str, cwd: str | None = None) -> dict:
    args = {"command": command} if cwd is None else {"command": command, "cwd": cwd}
    return {"tool_name": "mcp__terminal__run_in_terminal", "tool_input": args, "cwd": str(ROOT)}


def tool(name: str, *parts: str) -> dict:
    return {"tool_name": name, "tool_input": {"file_path": str(ROOT.joinpath(*parts))}}


def test_claude_hook_blocks_breaches_and_allows_normal_work():
    tables = str(ROOT / "data" / "tables" / "dim_part.csv")
    private_list = "C:\\Users\\x\\AppData\\Local\\fjordvik-guardrails\\banned-terms.txt"
    blocked = [
        bash("cat mcp/.env"),
        powershell("Get-Content mcp\\.env"),
        tool("Read", "mcp", ".env"),
        {"tool_name": "Write", "tool_input": {"file_path": tables}},
        tool("Edit", "data", "corpus", "x.md"),
        bash("git add ."),
        bash("git add -A"),
        bash("git add -u"),
        bash("git commit -am 'x'"),
        bash("git commit --no-verify -m x"),
        bash("git commit -n -m x"),
        bash("git push --force origin main"),
        # D8: .env outside a quoted search pattern on piped input
        bash("cat .env | grep x"),
        bash('grep "\\.env" .env'),
        bash('grep -rn "\\.env" .'),
        bash('git ls-files | grep -f ".env"'),
        bash('git ls-files | grep "$(cat .env)"'),
        powershell('git ls-files | Select-String -Path ".env" -Pattern a'),
        bash("type .env"),
        bash("cp .env /tmp/x"),
        # D3: shell writes into the generated folders
        bash("echo x > data/tables/dim_part.csv"),
        bash("sed -i s/a/b/ data/tables/dim_part.csv"),
        bash("rm -r data/tables"),
        bash("cp new.csv data/corpus/"),
        powershell("Set-Content data\\tables\\dim_part.csv x"),
        bash("rm tables/dim_part.csv", cwd=ROOT / "data"),
        bash("cd data && echo x >> tables/dim_part.csv"),
        # D3: other spellings of the same folders (Windows ignores case; .. steps back)
        tool("Write", "Data", "tables", "x.csv"),
        tool("Edit", "data", "src", "..", "tables", "x.csv"),
        bash("echo x > Data/Tables/dim_part.csv"),
        bash("echo x > data/src/../tables/dim_part.csv"),
        # D2: the private banned-names list
        {"tool_name": "Read", "tool_input": {"file_path": private_list}},
        powershell(f"Get-Content {private_list}"),
        powershell("Get-ChildItem $env:LOCALAPPDATA\\fjordvik-guardrails"),
        # fail closed: input the hook can't read
        "not json",
        # Monitor and terminal tool commands are checked like Bash and PowerShell
        monitor("cat mcp/.env"),
        terminal("Set-Content data\\tables\\x.csv x"),
        terminal("Remove-Item tables\\x.csv", cwd="data"),
        terminal("Get-Content mcp\\.env"),
    ]
    allowed = [
        bash("git status"),
        bash("cat mcp/.env.example"),
        bash("git add data/src/x.py data/tables/y.csv"),
        bash("git commit -m 'Add a table' -- data/x.py"),
        bash("git push origin main"),
        tool("Read", "data", "tables", "dim_part.csv"),
        tool("Edit", "data", "src", "x.py"),
        # the proposal's command, and search patterns on piped file names
        bash('git diff --cached --name-only | grep -E "(^|/)\\.env(\\.|$)"'),
        powershell("git ls-files | Select-String -Pattern '\\.env$'"),
        bash("git ls-files | rg '(^|/)\\.env'"),
        # reading or restoring generated data, and redirects elsewhere
        bash("git restore data/tables/dim_part.csv"),
        bash("cat data/tables/dim_part.csv | head -5"),
        bash("ls data/tables 2>/dev/null"),
        bash(".venv/Scripts/python -m pytest -q > evidence/out.txt 2>&1", cwd=ROOT / "data"),
        # reading guardrail files, and writing a new proposal
        bash("cat GUARDRAILS.md"),
        tool("Read", "guardrails", "check.py"),
        tool("Write", "guardrails", "proposals", "2026-11-02-x-y.md"),
        bash("echo x > guardrails/proposals/2026-11-02-x-y.md"),
        # D2: a file name that only contains the private folder's name
        {"tool_name": "Read", "tool_input": {"file_path": "C:\\Users\\x\\Projects\\knowledge\\raw\\inbox\\"
                                                          "2026-11-02-attena-fjordvik-guardrails-second-edition.md"}},
        monitor("tail -f data/evidence/x.log"),
        monitor(ws="wss://example.test/events"),
        terminal("git status"),
    ]
    ask = [
        tool("Edit", "GUARDRAILS.md"),
        tool("Write", "GUARDRAILS.sha256"),
        tool("Edit", "guardrails", "check.py"),
        tool("Edit", ".claude", "settings.json"),
        tool("Write", ".claude", "settings.local.json"),
        bash("echo x >> GUARDRAILS.md"),
        powershell("Set-Content guardrails\\check.py x"),
        bash("rm guardrails/check.py guardrails/proposals/2026-11-02-x-y.md"),
        # G9: other spellings of the same files
        tool("Edit", "guardrails.md"),
        tool("Edit", "Guardrails", "check.py"),
        tool("Edit", "guardrails", "proposals", "..", "check.py"),
        bash("echo x > guardrails.md"),
        bash("echo x > guardrails/proposals/../check.py"),
        monitor("echo x >> GUARDRAILS.md"),
    ]
    # A chat whose project folder is a part: the root still comes from git (G9, D3)
    part = ROOT / "service-ai"
    in_part = [
        (tool("Edit", "GUARDRAILS.md"), "ask"),
        ({"tool_name": "Write", "tool_input": {"file_path": tables}}, "block"),
        (bash("echo x > ../GUARDRAILS.md"), "ask"),
        (bash("git status"), "allow"),
    ]
    assert {repr(c): run_hook(c) for c in blocked} == {repr(c): "block" for c in blocked}
    assert {repr(c): run_hook(c) for c in allowed} == {repr(c): "allow" for c in allowed}
    assert {repr(c): run_hook(c) for c in ask} == {repr(c): "ask" for c in ask}
    assert {repr(c): run_hook(c, part) for c, _ in in_part} == {repr(c): e for c, e in in_part}
