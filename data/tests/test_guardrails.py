"""GUARDRAILS.md: the shared guardrail tests, run in every part (guardrails/shared_tests.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "guardrails"))

from shared_tests import *  # noqa: E402,F401,F403  (the tests are collected from here)
