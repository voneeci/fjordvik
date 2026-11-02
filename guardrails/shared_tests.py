"""Guardrail tests every part runs. Each part's tests/test_guardrails.py imports these,
so a breach of GUARDRAILS.md fails every part's test run, not just one.

Maintained by Attena (see GUARDRAILS.md).
"""

import hashlib
import json
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
    """A throwaway repository with one breach per rule the checker covers."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "GUARDRAILS.md").write_text("rules\n", encoding="utf-8")
    (tmp_path / "GUARDRAILS.sha256").write_text("0" * 64 + "  GUARDRAILS.md\n", encoding="utf-8")
    (tmp_path / "dash.md").write_text("A sentence " + chr(0x2014) + " with a dash.\n", encoding="utf-8")
    (tmp_path / "quoted.md").write_text('As published: "data visualization" stays.\n', encoding="utf-8")
    (tmp_path / "spelling.md").write_text("We analyze the color of things.\n", encoding="utf-8")
    (tmp_path / "count.md").write_text("Fjordvik is five projects.\n", encoding="utf-8")
    (tmp_path / "key.py").write_text("KEY = 'sk-ant-" + "x" * 24 + "'\n", encoding="utf-8")
    (tmp_path / ".env").write_text("NAME=value\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("NAME=\n", encoding="utf-8")
    found = "\n".join(check.check(tmp_path))
    assert "GUARDRAILS.md: changed without updating" in found
    assert "W1 dash.md" in found
    assert "W2 spelling.md: American spelling 'analyze'" in found
    assert "W2 spelling.md: American spelling 'color'" in found
    assert "W5 count.md" in found
    assert "D8 key.py" in found
    assert "D8 .env:" in found or "D8 .env: a .env file" in found
    assert "quoted.md" not in found and ".env.example" not in found


def run_hook(call: dict) -> int:
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(call), text=True,
                          capture_output=True, env={"CLAUDE_PROJECT_DIR": str(ROOT),
                                                    "SYSTEMROOT": "C:\\Windows"}).returncode


def test_claude_hook_blocks_breaches_and_allows_normal_work():
    tables = str(ROOT / "data" / "tables" / "dim_part.csv")
    blocked = [
        {"tool_name": "Bash", "tool_input": {"command": "cat mcp/.env"}},
        {"tool_name": "PowerShell", "tool_input": {"command": "Get-Content mcp\\.env"}},
        {"tool_name": "Read", "tool_input": {"file_path": str(ROOT / "mcp" / ".env")}},
        {"tool_name": "Write", "tool_input": {"file_path": tables}},
        {"tool_name": "Edit", "tool_input": {"file_path": str(ROOT / "data" / "corpus" / "x.md")}},
        {"tool_name": "Bash", "tool_input": {"command": "git add ."}},
        {"tool_name": "Bash", "tool_input": {"command": "git add -A"}},
        {"tool_name": "Bash", "tool_input": {"command": "git add -u"}},
        {"tool_name": "Bash", "tool_input": {"command": "git commit -am 'x'"}},
        {"tool_name": "Bash", "tool_input": {"command": "git commit --no-verify -m x"}},
        {"tool_name": "Bash", "tool_input": {"command": "git commit -n -m x"}},
        {"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}},
    ]
    allowed = [
        {"tool_name": "Bash", "tool_input": {"command": "git status"}},
        {"tool_name": "Bash", "tool_input": {"command": "cat mcp/.env.example"}},
        {"tool_name": "Bash", "tool_input": {"command": "git add data/src/x.py data/tables/y.csv"}},
        {"tool_name": "Bash", "tool_input": {"command": "git commit -m 'Add a table' -- data/x.py"}},
        {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}},
        {"tool_name": "Read", "tool_input": {"file_path": tables}},
        {"tool_name": "Edit", "tool_input": {"file_path": str(ROOT / "data" / "src" / "x.py")}},
    ]
    assert [run_hook(c) for c in blocked] == [2] * len(blocked)
    assert [run_hook(c) for c in allowed] == [0] * len(allowed)
