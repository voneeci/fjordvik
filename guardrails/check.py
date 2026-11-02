"""Check the repository against the rules in GUARDRAILS.md that a script can check.

Run from anywhere:  python guardrails/check.py
Exit code 0 when clean, 1 with one line per finding otherwise. Every part's
tests/test_guardrails.py runs the same checks, and guardrails/pre-commit runs this
before each commit once Reece has installed it.

Maintained by Attena (see GUARDRAILS.md). Other chats suggest changes in
guardrails/proposals/ instead of editing this file.
"""

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 50 * 1024 * 1024
TEXT = {".md", ".py", ".csv", ".json", ".toml", ".txt", ".tmdl", ".html", ".sql", ".yaml",
        ".yml", ".ps1", ".mf", ".example", ""}
EM_DASH = chr(0x2014)
SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"),                 # Anthropic keys
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),                            # AWS access keys
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),                  # GitHub tokens
    re.compile(r"xox[abprs]-[A-Za-z0-9\-]{10,}"),               # Slack tokens
    re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\b\s*[:=]\s*['\"][^'\"\s]{16,}['\"]"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"),                    # other sk- style keys
    re.compile(r"(?i)\b(server|host|data source|uid|user id)\s*=[^;\n]*;[^\n]*"
               r"\b(password|pwd)\s*=\s*[^;\s'\"]{4,}"),       # connection strings
    re.compile(r"\b[a-z][a-z0-9+.\-]*://[^\s/:@'\"]+:[^\s/@'\"$<{]{3,}@"),  # user:pass@ URLs
    re.compile(r"(?i)\b(AccountKey|SharedAccessKey)=[A-Za-z0-9+/=]{20,}"),
]
AMERICAN = re.compile(
    r"\b(colors?|colored|coloring|organiz(?:e|es|ed|ing|ation|ations)"
    r"|analyz(?:e|es|ed|ing)|behaviors?|favorites?|labeled|labeling|modeling|modeled"
    r"|centers?|centered|optimiz(?:e|es|ed|ing|ation)|summariz(?:e|es|ed|ing)"
    r"|prioritiz(?:e|es|ed|ing)|recogniz(?:e|es|ed|ing)|standardiz(?:e|es|ed|ing)"
    r"|normaliz(?:e|es|ed|ing)|visualiz(?:e|es|ed|ing|ation|ations)|catalogs?|defense|gray)\b")
PROJECT_COUNT = re.compile(r"\b(four|five|two|three|several) (?:separate )?projects\b",
                           re.IGNORECASE)
CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
URL = re.compile(r"https?://\S+")
QUOTED = re.compile("\"[^\"\n]*\"|“[^”\n]*”")
# Optional private list of names that must never appear (one per line), kept outside
# the public repository so the list itself names no one.
BANNED_TERMS_FILE = (Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
                     / "fjordvik-guardrails" / "banned-terms.txt")
SKIP_PROSE_CHECKS = {"GUARDRAILS.md"}


def files(root: Path = ROOT) -> list[str]:
    """Every file git tracks or would add (untracked files that are not ignored)."""
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                         cwd=root, capture_output=True, text=True, check=True).stdout
    return sorted({p for p in out.splitlines() if (root / p).is_file()})


def prose(markdown: str) -> str:
    """Markdown without code, web addresses and quotations, so identifiers such as a
    `color` property, URLs and words quoted from a published source (kept exactly as
    published) are not taken for this repository's own writing."""
    for pattern in (CODE_BLOCK, INLINE_CODE, URL, QUOTED):
        markdown = pattern.sub("", markdown)
    return markdown


def banned_terms() -> list[str]:
    if not BANNED_TERMS_FILE.is_file():
        return []
    return [t.strip() for t in BANNED_TERMS_FILE.read_text(encoding="utf-8").splitlines()
            if t.strip() and not t.startswith("#")]


def line_of(text: str, index: int) -> int:
    return text[:index].count("\n") + 1


def check(root: Path = ROOT) -> list[str]:
    findings = []
    banned = [re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE) for t in banned_terms()]
    fingerprint = root / "GUARDRAILS.sha256"
    if not fingerprint.is_file():
        findings.append("GUARDRAILS.sha256: missing")
    else:
        recorded = fingerprint.read_text(encoding="utf-8").split()[0]
        actual = hashlib.sha256((root / "GUARDRAILS.md").read_bytes()).hexdigest()
        if recorded != actual:
            findings.append("GUARDRAILS.md: changed without updating GUARDRAILS.sha256 "
                            "(only Attena edits it; suggest changes in guardrails/proposals/)")
    for rel in files(root):
        path = root / rel
        name = Path(rel).name
        if rel.startswith("old historical folders/"):
            findings.append(f"G8 {rel}: the local copy of the old repositories must stay out of git")
            continue
        if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
            findings.append(f"D8 {rel}: a .env file must never be in git")
            continue
        if path.stat().st_size > MAX_BYTES:
            findings.append(f"D9 {rel}: {path.stat().st_size / 1e6:.1f} MB is over 50 MB")
        if Path(rel).suffix.lower() not in TEXT:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        markdown = rel.endswith(".md")
        own = prose(text) if markdown else text
        if EM_DASH in own:
            findings.append(f"W1 {rel}: {own.count(EM_DASH)} em dash(es)")
        if rel != "guardrails/check.py":
            for pattern in SECRET_PATTERNS:
                m = pattern.search(text)
                if m:
                    findings.append(f"D8 {rel}:{line_of(text, m.start())}: looks like a secret")
        for pattern in banned:
            m = pattern.search(text)
            if m:
                findings.append(f"D2 {rel}:{line_of(text, m.start())}: a name on the private banned list")
        if markdown and rel not in SKIP_PROSE_CHECKS:
            for m in AMERICAN.finditer(own):
                findings.append(f"W2 {rel}: American spelling '{m.group(0)}'")
            for m in PROJECT_COUNT.finditer(own):
                findings.append(f"W5 {rel}: '{m.group(0)}' (Fjordvik is one project in parts)")
    return findings


def main() -> int:
    findings = check()
    for f in findings:
        print(f)
    if not BANNED_TERMS_FILE.is_file():
        print("Notice: the private banned-names list (rule D2) is missing, so that check "
              "was skipped. See guardrails/README.md.")
    print(f"{len(findings)} guardrail findings" if findings else "Guardrails: no findings")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
