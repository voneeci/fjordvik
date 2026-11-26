"""Check the repository against the rules in GUARDRAILS.md that a script can check.

It also checks the fingerprints of the guardrail files (G9) and the layout (L1: every
file matches an entry in guardrails/layout.md; L3: document names; L4: evidence names
carry the run date as a valid calendar date; L5: no scratch or temporary names), which
needs Python 3.13 or later. Since 19 November 2026 it also reads GitHub Actions workflows
(G12), Bicep files (C1) and evidence files for client IP addresses (D18). Those checks
read text patterns, not YAML or Bicep semantics, so values they check must be literals.

Run from anywhere:  python guardrails/check.py
Exit code 0 when clean, 1 with one line per finding otherwise. Every part's
tests/test_guardrails.py runs the same checks, and guardrails/pre-commit runs this
before each commit once Reece has installed it.

Maintained by Attena (see GUARDRAILS.md). Other chats suggest changes in
guardrails/proposals/ instead of editing this file.
"""

import datetime
import hashlib
import ipaddress
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 50 * 1024 * 1024
TEXT = {".md", ".py", ".csv", ".json", ".toml", ".txt", ".tmdl", ".html", ".sql", ".yaml",
        ".yml", ".ps1", ".mf", ".example", "", ".js", ".mjs", ".cjs", ".css", ".bicep",
        ".bicepparam"}
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
    # Application Insights connection strings (D8: set from Bicep, never written in a file)
    re.compile(r"(?i)\bInstrumentationKey=[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"),
    # NAME_TOKEN=value lines, as an environment dump or a settings file prints them: an
    # upper-case name holding KEY, TOKEN, SECRET or PASSWORD and an unquoted 12-character value.
    re.compile(r"(?m)^\s*(?:export\s+|set\s+)?[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)"
               r"[A-Z0-9_]*\s*=\s*['\"]?(?![$<{])[^\s'\"#(),\[\]]{12,}"),
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
    "docs/learning": re.compile(r"^service-ai\.md$"),
    "guardrails/proposals": re.compile(r"^(\d{4}-\d{2}-\d{2}-[a-z0-9]+-[a-z0-9-]+|README)\.md$"),
    "docs/architecture/adr": re.compile(r"^\d{4}-[a-z0-9-]+\.md$"),
}
# G12: GitHub Actions workflows. A deploy job must run from main through the production
# environment, after a test job; no workflow may use pull_request_target, and only a deploy
# job may hold id-token: write. Read job by job, with comments removed.
WORKFLOWS = ".github/workflows/"
LOCAL_ACTIONS = ".github/actions/"
DEPLOY_STEP = re.compile(
    r"(?i)\buses\s*:\s*['\"]?azure/"  # every Azure action: login, arm-deploy, webapps-deploy,
                                      # container-apps-deploy-action, static-web-apps-deploy
    r"|containerapp|deploy-pages|upload-pages-artifact"
    r"|peaceiris/actions-gh-pages|jamesives/github-pages-deploy-action"
    r"|\baz\s+(?:deployment|webapp|acr|staticwebapp|functionapp)\b"
    r"|\bdocker\s+push\b|\bgit\s+push\b[^\n]*\bgh-pages\b")
LOCAL_ACTION_USE = re.compile(r"(?i)\buses\s*:\s*['\"]?\./(\.github/actions/[^\s'\"@]+)")
# id-token: write in any layout (block at any indent, or flow style {id-token: write}),
# or permissions: write-all.
GRANT = re.compile(r"(?i)\bid-token['\"]?\s*:\s*['\"]?write\b|\bpermissions\s*:\s*['\"]?write-all\b")
PRODUCTION = re.compile(r"(?m)environment\s*:\s*['\"]?production['\"]?\s*$"
                        r"|environment\s*:\s*\n\s+name\s*:\s*['\"]?production"
                        r"|environment\s*:\s*\{[^}]*\bname\s*:\s*['\"]?production")
MAIN_ONLY = re.compile(r"branches\s*:\s*\[\s*['\"]?main['\"]?\s*\]"
                       r"|branches\s*:\s*\n\s*-\s*['\"]?main['\"]?\s*(\n(?!\s*-)|$)")
YAML_COMMENT = re.compile(r"(?m)(^|\s)#.*$")
# C1: a number in Bicep, written bare (2) or, for a decimal, as json('0.2'), the only way
# Bicep can write one.
BICEP_NUMBER = r"(?:json\(\s*'([\d.]+)'\s*\)|([\d.]+))"
BICEP_COMMENT = re.compile(r"/\*.*?\*/|(^|\s)//[^\n]*", re.S | re.M)
# D18: public IP addresses in evidence files. IPv4 loopback, 0.0.0.0, private and
# link-local ranges are allowed, and so are dotted version numbers such as
# numpy==2.5.4.1, v3.13.1.0 or "version 2.31.0.5". IPv6 counts when it is a global address.
IPV4 = re.compile(r"(?<![\d.])((?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3})(?!\.?\d)(?![A-Za-z])")
VERSION_BEFORE = re.compile(r"(?i)(?:[a-z_-]|[=<>~!]=|@|\bversion\b\s*[:=]?\s*)$")
NOT_PUBLIC = re.compile(r"^(127\.|0\.0\.0\.0$|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.)")
IPV6 = re.compile(r"(?<![\w:.])((?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4})(?![\w:])")
# IPv6 counts only in the global unicast range, where every client address sits (the
# documentation range 2001:db8::/32 included, as for IPv4). This leaves out loopback,
# link-local and unique local addresses, and Python slices such as [::10] or [1::2].
GLOBAL_V6 = ipaddress.ip_network("2000::/3")
# Evidence files read for D18 even though other checks skip their type.
EVIDENCE_TEXT = {".log", ".har"}
# L5: names that look like scratch, temporary or backup files. Words a project needs
# (temp for temperature, copy, old, debug) are left out.
SCRATCH_NAME = re.compile(r"(?i)(^|[-_. ])(scratch|tmp|untitled|backup|bak)([-_. ]|$)"
                          r"|\.(log|tmp|bak|orig|swp)$|~$|\s")
GENERATED = ("data/tables/", "data/erp-extract/", "data/corpus/", "data/generator-truth/",
             "data/scenarios/")
# G9: the guardrail files GUARDRAILS.sha256 must fingerprint, so an edit the hook misses
# still fails the tests.
FINGERPRINTED = ("GUARDRAILS.md", "guardrails/claude_hook.py", "guardrails/check.py",
                 "guardrails/shared_tests.py", "guardrails/layout.md", ".claude/settings.json",
                 "data/tests/test_guardrails.py", "mcp/tests/test_guardrails.py",
                 "powerbi/tests/test_guardrails.py", "power-automate/tests/test_guardrails.py",
                 "service-ai/tests/test_guardrails.py")


def files(root: Path = ROOT) -> list[str]:
    """Every file git tracks or would add (untracked files that are not ignored). Untracked
    Python caches are left out: importing a guardrail module, as each part's guardrail test
    does, writes guardrails/__pycache__/, which no .gitignore covers. A tracked cache file
    still counts."""
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard",
                          "--exclude=__pycache__/", "--exclude=*.pyc"],
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


def yaml_blocks(lines: list[str], indent: int) -> dict[str, str]:
    """The keys at one indent and the text under each (key line included), for a YAML file
    read as text. Keys may be quoted ("on":). Lines deeper than the indent belong to the
    key above them."""
    blocks: dict[str, list[str]] = {}
    key = None
    for line in lines:
        if not line.strip():
            continue
        depth = len(line) - len(line.lstrip(" "))
        if depth <= indent:
            m = re.match(r"\s*(['\"]?)([\w.-]+)\1\s*:", line)
            key = m.group(2) if m and depth == indent else None
            if key:
                blocks.setdefault(key, [])
        if key:
            blocks[key].append(line)
    return {k: "\n".join(v) for k, v in blocks.items()}


def workflow_jobs(jobs_text: str) -> dict[str, str]:
    """Each job under jobs:, by name."""
    lines = jobs_text.split("\n")[1:]
    first = next((l for l in lines if l.strip()), None)
    if first is None:
        return {}
    return yaml_blocks(lines, len(first) - len(first.lstrip(" ")))


def workflow_findings(rel: str, text: str, deploy_actions: frozenset[str] = frozenset()) -> list[str]:
    """G12 for one GitHub Actions workflow, read job by job. A deploy job is one with a deploy
    step, or one that uses a local action (.github/actions/) holding a deploy step."""
    text = YAML_COMMENT.sub(r"\1", text)
    found = []
    if "pull_request_target" in text:
        found.append(f"G12 {rel}: pull_request_target runs pull request code with the "
                     "repository's secrets; never use it")
    top = yaml_blocks(text.split("\n"), 0)
    outside = "\n".join(v for k, v in top.items() if k != "jobs")
    if GRANT.search(outside):
        found.append(f"G12 {rel}: id-token: write (or write-all) is granted to the whole "
                     "workflow; grant it to the deploy job only")
    jobs = workflow_jobs(top.get("jobs", ""))
    if not jobs and DEPLOY_STEP.search(text):
        jobs = {"(whole file)": text}  # a layout the reader can't split: judge it as one job

    def deploys(job: str) -> bool:
        used = {u.rstrip("/").lower() for u in LOCAL_ACTION_USE.findall(job)}
        return bool(DEPLOY_STEP.search(job) or used & deploy_actions)

    deploy = [name for name, job in jobs.items() if deploys(job)]
    for name, job in jobs.items():
        if name not in deploy and GRANT.search(job):
            found.append(f"G12 {rel}: job {name} holds id-token: write (or write-all) but has no "
                         "deploy step; grant it to the deploy job only")
    if deploy:
        triggers = top.get("on", "")
        if not MAIN_ONLY.search(triggers) or re.search(r"\bpull_request\b", triggers):
            found.append(f"G12 {rel}: a deploy workflow runs on pushes to main only, never on "
                         "pull requests")
    for name in deploy:
        if not PRODUCTION.search(jobs[name]):
            found.append(f"G12 {rel}: deploy job {name} must use the GitHub environment production")
        if not re.search(r"(?m)^\s+needs\s*:", jobs[name]):
            found.append(f"G12 {rel}: deploy job {name} needs a test job first (needs:)")
    return found


def deploy_actions(texts: dict[str, str]) -> frozenset[str]:
    """Local actions (.github/actions/<name>/action.yml) that hold a deploy step, as the
    folder a workflow's uses: line names."""
    return frozenset(rel.rsplit("/", 1)[0].lower() for rel, text in texts.items()
                     if DEPLOY_STEP.search(YAML_COMMENT.sub(r"\1", text)))


def bicep_numbers(pattern: str, text: str) -> list[float]:
    """Every value of a Bicep property, bare (2) or written json('0.2')."""
    return [float(a or b) for a, b in re.findall(rf"(?i)\b{pattern}\s*:\s*{BICEP_NUMBER}", text)]


def bicep_findings(texts: dict[str, str]) -> list[str]:
    """C1 across every Bicep file: replica caps, the smallest CPU and memory pair, a log cap,
    a budget with alerts at 50% and 100%, no private endpoint. Comments are ignored and
    resource types are matched in any case, as Bicep does. The values must be literals in
    the Bicep, so the caps are visible in review."""
    found = []
    clean = {rel: BICEP_COMMENT.sub(lambda m: m.group(1) or "", text) for rel, text in texts.items()}
    for rel, text in clean.items():
        if re.search(r"(?i)Microsoft\.Network/privateEndpoints", text):
            found.append(f"C1 {rel}: no private endpoint (it adds an hourly charge)")
        if re.search(r"(?i)Microsoft\.App/containerApps", text):
            mins = bicep_numbers("minReplicas", text)
            maxs = bicep_numbers("maxReplicas", text)
            cpus = bicep_numbers("cpu", text)
            memory = [float(m) for m in re.findall(r"(?i)\bmemory\s*:\s*'([\d.]+)\s*Gi'", text)]
            if not mins or any(m != 0 for m in mins):
                found.append(f"C1 {rel}: a container app needs minReplicas: 0")
            if not maxs or any(m > 2 for m in maxs):
                found.append(f"C1 {rel}: a container app needs maxReplicas of 2 or less")
            if not cpus or not memory or any(c > 0.25 for c in cpus) or any(m > 0.5 for m in memory):
                found.append(f"C1 {rel}: a container app needs the smallest CPU and memory pair "
                             "(cpu: json('0.25'), memory: '0.5Gi')")
        if re.search(r"(?i)Microsoft\.OperationalInsights/workspaces", text):
            caps = bicep_numbers("dailyQuotaGb", text)
            if not caps or any(c > 0.2 for c in caps):
                found.append(f"C1 {rel}: a Log Analytics workspace needs dailyQuotaGb of 0.2 or less")
    joined = "\n".join(clean.values())
    if re.search(r"(?i)Microsoft\.App/containerApps", joined):
        budgets = [part for part in re.split(r"(?im)^\s*resource\s", joined)
                   if re.search(r"(?i)Microsoft\.Consumption/budgets", part)]
        amounts = [bicep_numbers("amount", b) for b in budgets]
        if not budgets or not all(a and max(a) <= 5 for a in amounts):
            found.append("C1 (Bicep): a container app needs a Microsoft.Consumption/budgets "
                         "resource with amount of 5 or less")
        elif not any({50.0, 100.0} <= set(bicep_numbers("threshold", b)) for b in budgets):
            found.append("C1 (Bicep): the budget needs alerts at 50% and 100% "
                         "(threshold: 50 and threshold: 100)")
    return found


def public_addresses(text: str) -> str | None:
    """The first public IP address in an evidence file's text (D18), or None."""
    for m in IPV4.finditer(text):
        if NOT_PUBLIC.match(m.group(1)) or VERSION_BEFORE.search(text[max(0, m.start() - 12):m.start()]):
            continue
        return m.group(1)
    for m in IPV6.finditer(text):
        try:
            address = ipaddress.IPv6Address(m.group(1))
        except ValueError:
            continue
        if address in GLOBAL_V6:
            return m.group(1)
    return None


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
    bicep: dict[str, str] = {}
    tracked = files(root)
    actions = deploy_actions({rel: (root / rel).read_text(encoding="utf-8", errors="replace")
                              for rel in tracked if rel.startswith(LOCAL_ACTIONS)
                              and rel.endswith(("/action.yml", "/action.yaml"))})
    for rel in tracked:
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
        evidence = "/evidence/" in f"/{rel}"
        suffix = Path(rel).suffix.lower()
        if suffix not in TEXT and not (evidence and suffix in EVIDENCE_TEXT):
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
        if rel.startswith(WORKFLOWS) and rel.endswith((".yml", ".yaml")):
            findings += workflow_findings(rel, text, actions)
        if rel.lower().endswith(".bicep"):
            bicep[rel] = text
        if evidence:
            address = public_addresses(text)
            if address:
                findings.append(f"D18 {rel}:{line_of(text, text.index(address))}: looks like a "
                                "public IP address; evidence holds no client data")
        if markdown and rel not in SKIP_PROSE_CHECKS:
            for m in AMERICAN.finditer(own):
                findings.append(f"W2 {rel}: American spelling '{m.group(0)}'")
            for m in PROJECT_COUNT.finditer(own):
                findings.append(f"W5 {rel}: '{m.group(0)}' (Fjordvik is one project in parts)")
    findings += bicep_findings(bicep)
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
