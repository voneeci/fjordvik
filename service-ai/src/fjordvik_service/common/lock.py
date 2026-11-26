"""The split lock (E1): the dates and the settings chosen on validation, frozen before any test run."""

import json
from pathlib import Path

from .stamps import sha256_file, sha256_json


class LockError(RuntimeError):
    """The test run may not start: the lock is missing, or what it pins has changed."""


def write_lock(lock_path, evaluation_path, settings, chosen_from, extra):
    ev = json.loads(Path(evaluation_path).read_text(encoding="utf-8"))
    lock = {
        "rule": "E1: dates fixed before building; settings chosen on validation only; written before the first test run",
        "evaluation_sha256": sha256_file(evaluation_path),
        "periods": ev["periods"],
        "settings": settings,
        "settings_sha256": sha256_json(settings),
        "chosen_from": chosen_from,
        **extra,
    }
    # Unix line endings, the bytes git keeps for eval/, so the lock reads the same in any checkout.
    Path(lock_path).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8", newline="\n")
    return lock


def check_lock(lock_path, evaluation_path):
    """Return the frozen settings, or raise LockError."""
    lock_path = Path(lock_path)
    if not lock_path.exists():
        raise LockError(f"no split lock at {lock_path}: run the validation step first")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("evaluation_sha256") != sha256_file(evaluation_path):
        raise LockError("evaluation.json has changed since the split lock was written")
    ev = json.loads(Path(evaluation_path).read_text(encoding="utf-8"))
    if lock.get("periods") != ev["periods"]:
        raise LockError("the lock's dates differ from evaluation.json")
    if lock.get("settings_sha256") != sha256_json(lock.get("settings")):
        raise LockError("the lock's settings do not match their hash")
    return lock["settings"]
