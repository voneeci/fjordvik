"""The evaluation set (A9, E1): dates, counts and settings read from eval/ml/evaluation.json.

Code never types a date: every period, cut-off and alert window comes from that file, and
every file it rests on is checked against its SHA-256 before a step runs.
"""

import json
from pathlib import Path

import pandas as pd

from ..common.stamps import sha256_file

SERVICE_AI_DIR = Path(__file__).resolve().parents[3]
REPO_DIR = SERVICE_AI_DIR.parent
EVAL_DIR = SERVICE_AI_DIR / "eval" / "ml"
EVALUATION_PATH = EVAL_DIR / "evaluation.json"
ALLOWLIST_PATH = EVAL_DIR / "feature_allowlist.json"
LOCK_PATH = EVAL_DIR / "split_lock.json"
RUN_LOG = EVAL_DIR / "test_runs.jsonl"
SCENARIO_DIR = SERVICE_AI_DIR / "build" / "ml-scenarios"
PLANNING_INPUTS = REPO_DIR / "data" / "scenarios" / "planning_inputs.json"
TABLES_DIR = REPO_DIR / "data" / "tables"


class RestsOnError(RuntimeError):
    """A file the evaluation set rests on has changed, so no result would count."""


def load_evaluation(path=EVALUATION_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_allowlist(path=ALLOWLIST_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_rests_on(ev, repo_dir=REPO_DIR):
    """Stop when any file named under rests_on differs from its recorded SHA-256."""
    for rel, expected in ev["rests_on"]["sha256"].items():
        actual = sha256_file(Path(repo_dir) / rel)
        if actual != expected:
            raise RestsOnError(f"{rel} has changed since the evaluation set was written "
                               f"({actual[:12]} against {expected[:12]})")


def check_scenarios(scenario_dir=SCENARIO_DIR, manifest=REPO_DIR / "data" / "scenarios" / "manifest.json"):
    """The built scenario files must match data/scenarios/manifest.json byte for byte."""
    files = json.loads(Path(manifest).read_text(encoding="utf-8"))["files"]
    for rel, info in files.items():
        path = Path(scenario_dir) / rel
        if not path.exists():
            raise RestsOnError(f"scenario file missing: {path}; build it with python -m fjordvik_data.scenarios")
        if sha256_file(path) != info["sha256"]:
            raise RestsOnError(f"scenario file {rel} differs from data/scenarios/manifest.json")


def day(text):
    return pd.Timestamp(text)


def period(ev, name):
    """One period's dates as timestamps: scored days, cut-off and alert window."""
    p = ev["periods"][name]
    window = p["alert_window"]
    first = p["first_scored_day"]
    return {
        "name": name,
        # Train starts at each pump's first complete row, so it has no fixed first day.
        "first_scored": day(first) if first[:2] == "20" else None,
        "last_scored": day(p["last_scored_day"]),
        "cut_off": day(p["cut_off"]),
        "alert_first": day(window["first_day"]) if window else None,
        "alert_last": day(window["last_day"]) if window else None,
        "alert_days": window["days"] if window else None,
    }


def periods(ev):
    return {name: period(ev, name) for name in ["train", "validation", "test"]}


def failure_period_bounds(ev):
    """Which period a failure falls in, by reported_date (expected_counts.failures)."""
    p = periods(ev)
    return {
        "train": (None, p["train"]["cut_off"]),
        "validation": (p["validation"]["alert_first"], p["validation"]["cut_off"]),
        "test": (p["test"]["alert_first"], p["test"]["cut_off"]),
    }


def no_label_window(ev):
    w = ev["periods"]["no_complete_label_window"]
    return day(w["first_day"]), day(w["last_day"])
