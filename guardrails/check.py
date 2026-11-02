"""Check the repository against the rules in GUARDRAILS.md that a script can check.

It also checks the fingerprints of the guardrail files (G9) and the layout (L1: every
file matches an entry in guardrails/layout.md; L3: document names; L4: evidence names
carry the run date as a valid calendar date; L5: no scratch or temporary names), which
needs Python 3.13 or later.

Run from anywhere:  python guardrails/check.py
Exit code 0 when clean, 1 with one line per finding otherwise. Every part's
tests/test_guardrails.py runs the same checks, and guardrails/pre-commit runs this
before each commit once Reece has installed it.

Maintained by Attena (see GUARDRAILS.md). Other chats suggest changes in
guardrails/proposals/ instead of editing this file.
"""

import datetime
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

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
# The layout map (rules L1 to L6): one "- `pattern`: purpose" line per allowed place.
LAYOUT = PurePosixPath("guardrails/layout.md")
LAYOUT_ENTRY = re.compile(r"^- `([^`]+)`", re.MULTILINE)
LAYOUT_PARTS = re.compile(r"^Parts:\s*(.+)$", re.MULTILINE)
EVIDENCE_NAME = re.compile(r"^([a-z0-9-]*-)?20[2-9]\d-\d{2}-\d{2}(-[a-z0-9-]*)?\.[a-z0-9]+$")
DATE = re.compile(r"(?<!\d)\d{4}-\d{2}-\d{2}(?!\d)")
# L3: names in the folders that hold one kind of document each.
DOCUMENT_NAMES = {
    "docs/handover": re.compile(r"^\d{4}-\d{2}-\d{2}-fjordvik-[a-z0-9-]+\.md$"),
    "docs/learning": re.compile(r"^phase\d+-[a-z0-9-]+\.md$"),
    "guardrails/proposals": re.compile(r"^(\d{4}-\d{2}-\d{2}-[a-z0-9]+-[a-z0-9-]+|README)\.md$"),
}
# L5: names that look like scratch, temporary or backup files. Words a project needs
# (temp for temperature, copy, old, debug) are left out.
SCRATCH_NAME = re.compile(r"(?i)(^|[-_. ])(scratch|tmp|untitled|backup|bak)([-_. ]|$)"
                          r"|\.(log|tmp|bak|orig|swp)$|~$|\s")
GENERATED = ("data/tables/", "data/erp-extract/", "data/corpus/", "data/generator-truth/")
# G9: the guardrail files GUARDRAILS.sha256 must fingerprint, so an edit the hook misses
# still fails the tests.
FINGERPRINTED = ("GUARDRAILS.md", "guardrails/claude_hook.py", "guardrails/check.py",
                 "guardrails/shared_tests.py", "guardrails/layout.md", ".claude/settings.json",
                 "data/tests/test_guardrails.py", "mcp/tests/test_guardrails.py",
                 "powerbi/tests/test_guardrails.py", "power-automate/tests/test_guardrails.py",
                 "service-ai/tests/test_guardrails.py")


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


def layout(root: Path = ROOT) -> tuple[list[str], list[str]] | None:
    """The layout map's patterns, with <part> written out for each part, and the parts.
    Only entries after the Parts: line count, so examples in the introduction don't.
    None when the map is missing; no parts and no patterns when Parts: is missing."""
    path = root / LAYOUT
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    found = LAYOUT_PARTS.search(text)
    if not found:
        return [], []
    parts = [p.strip() for p in found.group(1).split(",")]
    patterns = []
    for entry in LAYOUT_ENTRY.findall(text[found.end():]):
        patterns += [entry.replace("<part>", p) for p in parts] if "<part>" in entry else [entry]
    return patterns, parts


def real_date(name: str) -> bool:
    """True when the name holds at least one real calendar date (YYYY-MM-DD)."""
    for found in DATE.findall(name):
        try:
            datetime.date.fromisoformat(found)
            return True
        except ValueError:
            pass
    return False


def name_findings(rel: str, parts: list[str], explicit: set[str]) -> list[str]:
    """L3, L4 and L5 findings for one file's name."""
    p = PurePosixPath(rel)
    folder, name = str(p.parent), p.name
    found = []
    # Power BI names the files in its project folders after model objects (a role named
    # "Rest of world" is "Rest of world.tmdl"), so L5 leaves those folders alone.
    tool_named = (len(p.parts) > 2 and p.parts[1].endswith((".Report", ".SemanticModel"))
                  or rel.startswith(GENERATED))
    if any(SCRATCH_NAME.search(part) for part in p.parts) and not tool_named:
        found.append(f"L5 {rel}: looks like a scratch, temporary or backup file; keep those "
                     "in the chat's scratchpad")
    rule = DOCUMENT_NAMES.get(folder)
    if rule and (not rule.match(name) or (DATE.match(name) and not real_date(name))):
        found.append(f"L3 {rel}: name doesn't follow the pattern for {folder}/ in GUARDRAILS.md L3")
    evidence = (len(p.parts) == 3 and p.parts[1] == "evidence"
                and (p.parts[0] in parts or p.parts[0] == "guardrails"))
    if evidence and rel not in explicit and not (EVIDENCE_NAME.match(name) and real_date(name)):
        found.append(f"L4 {rel}: evidence names need lower case, hyphens and the run date "
                     "(YYYY-MM-DD)")
    return found


def fingerprint(path: Path) -> str:
    """SHA-256 of a file with CRLF line endings read as LF, so a checkout that converts
    line endings (core.autocrlf) doesn't change the fingerprint."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def fingerprint_findings(root: Path) -> list[str]:
    """GUARDRAILS.sha256 holds one line per guardrail file (hash, two spaces, path). Each
    must match, and every guardrail file that exists must be listed."""
    path = root / "GUARDRAILS.sha256"
    if not path.is_file():
        return ["GUARDRAILS.sha256: missing"]
    found, listed = [], set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        if len(line.split(None, 1)) < 2:
            found.append(f"GUARDRAILS.sha256: a line without a path ({line.strip()[:16]}...)")
            continue
        recorded, name = line.split(None, 1)
        name = name.strip()
        listed.add(name)
        target = root / name
        if not target.is_file():
            found.append(f"{name}: listed in GUARDRAILS.sha256 but missing")
        elif recorded != fingerprint(target):
            found.append(f"{name}: changed without updating GUARDRAILS.sha256 "
                         "(only Attena edits it; suggest changes in guardrails/proposals/)")
    for name in FINGERPRINTED:
        if (root / name).is_file() and name not in listed:
            found.append(f"{name}: not fingerprinted in GUARDRAILS.sha256 (rule G9)")
    return found


def line_of(text: str, index: int) -> int:
    return text[:index].count("\n") + 1


def check(root: Path = ROOT) -> list[str]:
    findings = []
    banned = [re.compile(rf"\b{re.escape(t)}\b", re.IGNORECASE) for t in banned_terms()]
    findings += fingerprint_findings(root)
    mapped = layout(root)
    if mapped is None:
        findings.append(f"L1 {LAYOUT}: missing")
    elif not mapped[1]:
        findings.append(f"L1 {LAYOUT}: no 'Parts:' line, so no entry can be read")
        mapped = None
    off_map: dict[str, list[str]] = {}
    for rel in files(root):
        path = root / rel
        name = Path(rel).name
        if rel.startswith("old historical folders/"):
            findings.append(f"G8 {rel}: the local copy of the old repositories must stay out of git")
            continue
        if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
            findings.append(f"D8 {rel}: a .env file must never be in git")
            continue
        if mapped:
            patterns, parts = mapped
            p = PurePosixPath(rel)
            if not any(p.full_match(pattern) for pattern in patterns):
                off_map.setdefault(str(p.parent), []).append(name)
            else:
                findings += name_findings(rel, parts, set(patterns))
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
    for folder, names in sorted(off_map.items()):
        where = "(root)" if folder == "." else f"{folder}/"
        findings.append(f"L1 {where}: {len(names)} file(s) not on the layout map ({LAYOUT}), "
                        f"e.g. {names[0]}")
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
