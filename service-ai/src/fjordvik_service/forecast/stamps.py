"""What every saved result names (G10, W8): the data checksum, the commit, the model version
and that it was measured on synthetic data with planted signals."""

import hashlib
import json
import subprocess
from pathlib import Path

from . import DATA_BASIS, MODEL_VERSION

STAMP_FIELDS = ["data_sha256", "commit", "model_version", "data_basis"]


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


def stamp(data_dir, commit):
    return {
        "data_sha256": data_checksum(data_dir),
        "commit": commit,
        "model_version": MODEL_VERSION,
        "data_basis": DATA_BASIS,
    }
