"""Guardrail tests every part runs. Each part's tests/test_guardrails.py imports these,
so a breach of GUARDRAILS.md fails every part's test run, not just one.

Maintained by Attena (see GUARDRAILS.md).
"""

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
    """GUARDRAILS.sha256 fingerprints every guardrail file check.FINGERPRINTED names."""
    lines = (ROOT / "GUARDRAILS.sha256").read_text(encoding="utf-8").splitlines()
    recorded = {name.strip(): digest for digest, name in (l.split(None, 1) for l in lines if l.strip())}
    assert set(check.FINGERPRINTED) <= set(recorded)
    for name, digest in recorded.items():
        assert digest == check.fingerprint(ROOT / name), name


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
    (tmp_path / "envdump.txt").write_text("PATH=/usr/bin\nMY_" + "TOKEN=" + "z" * 16 + "\n",
                                          encoding="utf-8")
    (tmp_path / ".env").write_text("NAME=value\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("NAME=\n", encoding="utf-8")
    # L1 and L4: a layout map, a stray folder and an evidence file with no run date
    (tmp_path / "guardrails").mkdir()
    (tmp_path / "guardrails" / "layout.md").write_text(
        "- `**`: an example before the Parts line, which must not count\n\n"
        "Parts: part\n\n- `*.md`: x\n- `*.py`: x\n- `*.txt`: x\n- `GUARDRAILS.sha256`: x\n"
        "- `.env.example`: x\n- `guardrails/*`: x\n- `guardrails/evidence/*`: x\n"
        "- `<part>/evidence/*`: x\n- `docs/handover/*.md`: x\n- `docs/learning/*.md`: x\n"
        "- `guardrails/proposals/*.md`: x\n- `<part>/src/**/*.py`: x\n", encoding="utf-8")
    (tmp_path / "guardrails" / "proposals").mkdir()
    (tmp_path / "guardrails" / "proposals" / "2026-11-02-x.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "part" / "src" / "scratch").mkdir(parents=True)
    (tmp_path / "part" / "src" / "scratch" / "x.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "part" / "src" / "pump_temp.py").write_text("x = 1\n", encoding="utf-8")
    # L3, L4, L5 and G9: names and fingerprints
    (tmp_path / "scratch-notes.md").write_text("notes\n", encoding="utf-8")
    (tmp_path / "docs" / "handover").mkdir(parents=True)
    (tmp_path / "docs" / "handover" / "notes.md").write_text("notes\n", encoding="utf-8")
    (tmp_path / "docs" / "learning").mkdir()
    (tmp_path / "docs" / "learning" / "phase3-x.md").write_text("notes\n", encoding="utf-8")
    (tmp_path / "docs" / "learning" / "service-ai.md").write_text("notes\n", encoding="utf-8")
    (tmp_path / "guardrails" / "evidence").mkdir()
    (tmp_path / "guardrails" / "evidence" / "run.txt").write_text("1 passed\n", encoding="utf-8")
    (tmp_path / "guardrails" / "check.py").write_text("# x\n", encoding="utf-8")
    (tmp_path / "scratch").mkdir()
    (tmp_path / "scratch" / "notes.md").write_text("notes\n", encoding="utf-8")
    (tmp_path / "part" / "evidence").mkdir(parents=True)
    (tmp_path / "part" / "evidence" / "run.txt").write_text("1 passed\n", encoding="utf-8")
    (tmp_path / "part" / "evidence" / "pytest-x-2026-11-02.txt").write_text("1 passed\n",
                                                                            encoding="utf-8")
    (tmp_path / "part" / "evidence" / "pytest-x-2026-13-45.txt").write_text("1 passed\n",
                                                                            encoding="utf-8")
    found = "\n".join(check.check(tmp_path))
    assert "GUARDRAILS.md: changed without updating" in found
    assert "W1 dash.md" in found
    assert "W2 spelling.md: American spelling 'analyze'" in found
    assert "W2 spelling.md: American spelling 'color'" in found
    assert "W5 count.md" in found
    for name in ("key.py", "otherkey.py", "conn.txt", "url.md", "azure.txt", "envdump.txt"):
        assert f"D8 {name}" in found, name
    assert "D8 .env:" in found or "D8 .env: a .env file" in found
    assert "quoted.md" not in found and ".env.example" not in found
    assert "placeholder.md" not in found
    assert "L1 scratch/: 1 file(s) not on the layout map" in found
    assert "L4 part/evidence/run.txt" in found
    assert "pytest-x-2026-11-02.txt" not in found and "L1 (root)" not in found
    assert "L5 scratch-notes.md" in found
    assert "L3 docs/handover/notes.md" in found
    assert "L3 docs/learning/phase3-x.md" in found
    assert "L3 docs/learning/service-ai.md" not in found
    assert "L4 guardrails/evidence/run.txt" in found
    assert "L4 part/evidence/pytest-x-2026-13-45.txt" in found
    assert "guardrails/check.py: not fingerprinted" in found
    assert "L3 guardrails/proposals/2026-11-02-x.md" in found
    assert "L5 part/src/scratch/x.py" in found and "pump_temp" not in found
    (tmp_path / "GUARDRAILS.sha256").write_text("0" * 64 + "\n", encoding="utf-8")
    assert "GUARDRAILS.sha256: a line without a path" in "\n".join(check.check(tmp_path))
    (tmp_path / "guardrails" / "layout.md").write_text("- `**`: x\n", encoding="utf-8")
    assert "no 'Parts:' line" in "\n".join(check.check(tmp_path))


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
        # From the guardrails test of 2 November 2026: git forms (G1 to G3)
        bash("git -C . add -A"),
        bash("git stage -A"),
        bash("git add :/"),
        bash("git add *"),
        bash("git -C . commit -n -m x"),
        bash("git push origin +main"),
        bash("git commit --no-verif -m x"),
        bash("git push --forc origin main"),
        bash("git config core.hooksPath x"),
        # D3 from inside the generated folders, by deleting a parent, and other writers
        bash("rm x.csv", cwd=ROOT / "data" / "tables"),
        bash("cd data/tables && rm x.csv"),
        terminal("Remove-Item x.csv", cwd="data\\tables"),
        bash("rm -rf data"),
        powershell("Remove-Item -Recurse -Force data"),
        powershell("Import-Csv a.csv | Export-Csv data\\tables\\x.csv"),
        bash("python -c \"open('data/tables/x.csv','w').write('x')\""),
        # D3 path forms, D8 and D2 forms
        {"tool_name": "Write", "tool_input": {"file_path": "\\\\?\\" + tables}},
        tool("Write", "data", "tables.", "x.csv"),
        {"tool_name": "Write", "tool_input": {"file_path": "..\\data\\tables\\x.csv"},
         "cwd": str(ROOT / "service-ai")},
        tool("Read", "no-such-folder", ".ENV"),
        bash("cat no-such-folder/.e*"),
        {"tool_name": "Grep", "tool_input": {"pattern": "x", "path": str(ROOT / "mcp"),
                                             "glob": ".env"}},
        {"tool_name": "Grep", "tool_input": {"pattern": "x", "path": "C:\\Users\\x",
                                             "glob": "banned*"}},
        # From the re-test of 2 November 2026: wrapped commands, writers, redirects, moves
        bash("bash -c 'echo; rm data/tables/x.csv'"),
        bash("cmd /c \"del data\\tables\\x.csv\""),
        powershell("powershell -Command \"Remove-Item data\\tables\\x.csv\""),
        bash("ls &>> data/tables/x.csv"),
        bash("curl -o data/tables/x.csv https://example.test/x"),
        powershell("Get-Date | Tee-Object -FilePath data\\tables\\x.csv"),
        bash("(cd data/tables && rm x.csv)"),
        bash("python - <<'EOF'\nopen('data/tables/x.csv', 'w').write('x')\nEOF"),
        bash("mv data data-old"),
        bash("git rm data/tables/x.csv"),
        bash("git add ..", cwd=ROOT / "service-ai"),
        bash("git commit -m x ."),
        bash("git push --mirror origin"),
        bash("git add \\\n -A"),
        powershell("& git add -A"),
        # G2: git hooks; D8: PowerShell wildcards and tools that send files
        bash("rm .git/hooks/pre-commit"),
        tool("Edit", ".git", "hooks", "pre-commit"),
        powershell("Get-Content mcp\\*env"),
        {"tool_name": "SendUserFile", "tool_input": {"files": ["mcp/.env"]}, "cwd": str(ROOT)},
        {"tool_name": "Artifact", "tool_input": {"file_path": str(ROOT / "mcp" / ".env")}},
        {"tool_name": "mcp__claude-artifacts__publish_files", "cwd": str(ROOT),
         "tool_input": {"files": [{"as": "index.html", "path": str(ROOT / "mcp" / ".env")}]}},
        {"tool_name": "mcp__claude-artifacts__upload_asset", "cwd": str(ROOT),
         "tool_input": {"slug": "x", "files": [{"name": "a.txt", "path": str(ROOT / "mcp" / ".env")}]}},
        # From the final re-test of 3 November 2026. "git checkout <old> -- ." was an ask
        # (G9); it now blocks, because it also restores old generated tables (D3).
        bash("git checkout dd6370b -- ."),
        bash("git checkout b7b9203 -- data/tables"),
        bash("git restore --source=HEAD~3 data/tables/dim_part.csv"),
        bash("python -c \"import os; open(os.path.join('data', 'tables', 'x.csv'), 'w')\""),
        bash("python - <<'EOF'\nfrom pathlib import Path\nout = Path('data') / 'tables' / 'x.csv'\n"
             "out.write_text('x')\nEOF"),
        bash("python - <<'EOF'\nROOT = 'C:/x'\nimport pandas as pd\n"
             "pd.DataFrame().to_csv(f'{ROOT}/data/tables/x.csv')\nEOF"),
        # D8: printing the environment or a key
        bash("env"),
        bash("printenv | sort"),
        powershell("Get-ChildItem env:"),
        bash("echo $ANTHROPIC_API_KEY"),
        powershell("$env:ANTHROPIC_API_KEY"),
        bash("python -c \"import os; print(os.environ['ANTHROPIC_API_KEY'])\""),
        bash("gh auth token"),
        # From the scoped re-test of 3 November 2026: other spellings of the environment,
        # Path.open, constants plus parts, and deletes fed through a pipe
        powershell("Get-ChildItem Env:\\"),
        powershell("Get-Item Env:\\ANTHROPIC_API_KEY"),
        powershell("[Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY', 'User')"),
        bash("export | grep -i api"),
        bash("python - <<'EOF'\nimport os\nfor k in os.environ:\n    print(k, os.environ[k])\nEOF"),
        bash("python - <<'EOF'\nfrom pathlib import Path\nwith Path('data/tables/x.csv').open('w') as f:\n"
             "    f.write('x')\nEOF"),
        bash("python - <<'EOF'\nfrom pathlib import Path\nimport pandas as pd\n"
             "TABLES = Path('data') / 'tables'\npd.DataFrame().to_csv(TABLES / 'dim_part.csv')\nEOF"),
        powershell("Get-ChildItem data\\tables -Filter *.csv | Remove-Item"),
        bash("ls data/tables/*.csv | xargs rm"),
        bash("git ls-files data/tables | xargs rm"),
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
        # Work the stricter checks must still allow
        bash("git add data/tables/*.csv data/src/x.py"),
        bash("cd data && python -m fjordvik_data --out tables"),
        bash("mv data/src/a.py data/src/b.py"),
        bash("git push --follow-tags origin main"),
        bash("python -c \"print(1)\""),
        bash("rm *.pyc", cwd=ROOT / "service-ai"),
        {"tool_name": "Grep", "tool_input": {"pattern": "x", "path": str(ROOT), "glob": "*.py"}},
        # Everyday work the re-test of 2 November 2026 found blocked
        bash("git add a.py && git commit -m x -- a.py && git push -u origin main"),
        bash("git commit -m x -- a.py && git log -n 3 --oneline"),
        bash("git commit -m 'Ignore .env files' -- mcp/.gitignore"),
        bash("cp data/tables/dim_part.csv mcp/tests/fixtures/dim_part.csv"),
        bash("tar -czf /tmp/tables.tgz data/tables"),
        bash("python -c \"print(open('a.txt').read())\""),
        bash("git checkout -b feature/x"),
        bash("git restore --staged guardrails/check.py"),
        bash("echo \"Run 'echo x > data/tables/x.csv' to see the D3 block\" > notes.txt"),
        # From the final re-test of 3 November 2026: reading tables, caches, environment
        bash("python -c \"import pandas as pd; pd.read_csv('data/tables/x.csv')"
             ".to_csv('service-ai/results/x.csv')\""),
        bash("python -c \"import shutil; shutil.copy('data/tables/x.csv', 'mcp/tests/fixtures/x.csv')\""),
        bash("find . -name '*.pyc' -delete"),
        bash("find service-ai -name .pytest_cache -type d -exec rm -rf {} +"),
        bash("rm -rf */__pycache__"),
        bash("git restore data/tables/dim_part.csv"),
        bash("env PYTHONPATH=src python -m pytest -q"),
        bash("echo $PATH"),
        bash("python -c \"import os; print('ANTHROPIC_API_KEY' in os.environ)\""),
        {"tool_name": "SendUserFile", "tool_input": {"files": ["docs/company-profile.md"]},
         "cwd": str(ROOT)},
        {"tool_name": "mcp__claude-artifacts__publish_files", "cwd": str(ROOT),
         "tool_input": {"files": [{"as": "index.html", "path": str(ROOT / "docs" / "x.html")}]}},
        {"tool_name": "mcp__claude-artifacts__upload_asset", "cwd": str(ROOT),
         "tool_input": {"slug": "x", "files": [{"name": "a.png", "path": str(ROOT / "docs" / "a.png")}]}},
        # From the scoped re-test of 3 November 2026: set checks, reads, caches and pipes
        powershell("Test-Path Env:\\ANTHROPIC_API_KEY"),
        powershell("[Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY', 'User') -ne $null"),
        powershell("[Environment]::GetEnvironmentVariable('PATH', 'User')"),
        bash("python - <<'EOF'\nfrom pathlib import Path\nimport pandas as pd\n"
             "TABLES = Path('data') / 'tables'\nRESULTS = Path('service-ai') / 'results'\n"
             "pd.read_csv(TABLES / 'dim_part.csv').to_csv(RESULTS / 'x.csv')\nEOF"),
        powershell("Get-ChildItem -Recurse -Filter __pycache__ | Remove-Item -Recurse -Force"),
        bash("find . -path '*/__pycache__/*' -delete"),
        bash("git ls-files data/tables | wc -l"),
        bash("git checkout @ -- data/tables"),
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
        # G9 from inside guardrails/, through git, and in other path forms
        bash("rm check.py", cwd=ROOT / "guardrails"),
        bash("cd guardrails && rm check.py"),
        terminal("Remove-Item check.py", cwd="guardrails"),
        bash("git rm GUARDRAILS.md"),
        bash("git checkout dd6370b -- guardrails/claude_hook.py"),
        bash("rm -rf .claude"),
        {"tool_name": "Edit", "tool_input": {"file_path": "\\\\?\\" + str(ROOT / "GUARDRAILS.md")}},
        tool("Edit", "GUARDRAILS.md."),
        tool("Edit", "GUARDRAILS.md::$DATA"),
        # G9 rollbacks and moves, a part's guardrail test, and a command the hook can't read
        bash("git reset --hard dd6370b"),
        bash("git checkout dd6370b -- guardrails"),
        bash("mv .claude .claude-old"),
        powershell("Rename-Item .claude x"),
        tool("Edit", "service-ai", "tests", "test_guardrails.py"),
        bash("powershell -EncodedCommand AAAA"),
        # Moves the final re-test found, and other files in .claude/
        bash("mv -t /tmp .claude"),
        powershell("robocopy .claude C:\\temp\\x /MOVE"),
        tool("Write", ".claude", "hooks", "x.py"),
        bash("find . -name '*.py' -delete"),
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
