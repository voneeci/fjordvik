"""What every saved result names (G10, W8): the data checksum, the commit, the model version
and that it was measured on synthetic data with planted signals."""

import csv
import hashlib
import io
import json
import platform
import subprocess
from importlib.metadata import version
from pathlib import Path

STAMP_FIELDS = ["data_sha256", "commit", "model_version", "data_basis"]


def environment(libraries):
    """The exact Python and library versions behind a result (the pins allow a minor range)."""
    return {"python": platform.python_version(), **{name: version(name) for name in libraries}}


def scores_sha256(csv_text, drop=STAMP_FIELDS):
    """SHA-256 of a results table without its stamp columns, so reruns at a new commit compare."""
    rows = list(csv.reader(io.StringIO(csv_text)))
    keep = [i for i, name in enumerate(rows[0]) if name not in drop]
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    for row in rows:
        writer.writerow([row[i] for i in keep])
    return hashlib.sha256(out.getvalue().encode("utf-8")).hexdigest()


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def data_checksum(data_dir):
    """The SHA-256 of the data manifest, which pins every table's checksum."""
    return sha256_file(Path(data_dir) / "manifest.json")


def git_commit(repo_dir):
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True, check=True
    ).stdout.strip()


def uncommitted(repo_dir, paths):
    """Paths among `paths` with changes git has not committed (tracked or new)."""
    out = subprocess.run(
        ["git", "status", "--porcelain", "--", *[str(p) for p in paths]],
        cwd=repo_dir, capture_output=True, text=True, check=True,
    ).stdout
    return [line[3:] for line in out.splitlines() if line.strip()]


def stamp(data_dir, commit, model_version, data_basis):
    return {
        "data_sha256": data_checksum(data_dir),
        "commit": commit,
        "model_version": model_version,
        "data_basis": data_basis,
    }
