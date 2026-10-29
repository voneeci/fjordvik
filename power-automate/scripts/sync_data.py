"""Copy the Fjordvik CSV files from a fjordvik-data checkout and verify them.

Usage:  python scripts/sync_data.py [path-to-fjordvik-data]   (default: ../fjordvik-data)

Every file is checked against the SHA-256 checksum in the source manifest before
it is copied, so a hand-edited or half-written file can never slip in. The
source's git commit (and tag, if any) is recorded in data/SOURCE.json.
"""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEST = REPO / "data"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(source: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(source), *args],
                             capture_output=True, text=True, check=True)
        return out.stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO.parent / "fjordvik-data"
    src_data = source / "data"
    manifest = json.loads((src_data / "manifest.json").read_text(encoding="utf-8"))

    for name, info in manifest["tables"].items():
        path = src_data / info["file"]
        if sha256(path) != info["sha256"]:
            print(f"FAILED: {path} does not match its checksum in the manifest")
            return 1

    if git(source, "status", "--porcelain", "--", "data"):
        print("FAILED: fjordvik-data has uncommitted changes in data/. Commit them first.")
        return 1

    DEST.mkdir(exist_ok=True)
    for info in manifest["tables"].values():
        shutil.copyfile(src_data / info["file"], DEST / info["file"])
    shutil.copyfile(src_data / "manifest.json", DEST / "manifest.json")

    record = {
        "source_repository": "fjordvik-data",
        "commit": git(source, "rev-parse", "HEAD"),
        "tag": git(source, "describe", "--tags", "--exact-match"),
        "generator_version": manifest["generator_version"],
    }
    (DEST / "SOURCE.json").write_text(json.dumps(record, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
    print(f"Copied {len(manifest['tables'])} tables from {source} "
          f"(commit {record['commit']}, tag {record['tag']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
