"""Reconcile every DAX measure against the independent Python calculation.

Needs FjordvikEmissions.pbip open in Power BI Desktop (refreshed). Skipped otherwise.
Run:  python -m pytest tests/test_measures_live.py -v
"""

import json
import subprocess
from pathlib import Path

import pytest

from expected import cases, dax_query

REPO = Path(__file__).resolve().parents[1]
CASES = cases()


def desktop_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq PBIDesktop.exe"],
                         capture_output=True, text=True).stdout
    return "PBIDesktop.exe" in out


pytestmark = pytest.mark.skipif(not desktop_running(),
                                reason="Power BI Desktop is not running with the model open")


@pytest.fixture(scope="module")
def results(tmp_path_factory):
    queries = [{"id": c["id"], "query": dax_query(c), "role": c["role"]} for c in CASES]
    path = tmp_path_factory.mktemp("dax") / "queries.json"
    path.write_text(json.dumps(queries), encoding="utf-8")
    out = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
         str(REPO / "scripts" / "run_dax.ps1"), "-QueryFile", str(path)],
        capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, out.stderr
    return {r["id"]: r for r in json.loads(out.stdout)}


@pytest.mark.parametrize("c", CASES, ids=[c["id"] for c in CASES])
def test_measure_matches_python(c, results):
    r = results[c["id"]]
    assert r["error"] is None, f"{dax_query(c)}\n{r['error']}"
    if c["expected"] is None:
        assert r["value"] is None, f"expected blank, got {r['value']}"
    elif isinstance(c["expected"], str):
        # Text measures: the exact words, or the fixed start of words that hold a time.
        if c.get("prefix"):
            assert str(r["value"]).startswith(c["expected"]), r["value"]
        else:
            assert r["value"] == c["expected"], r["value"]
    else:
        assert r["value"] is not None, "got blank"
        assert abs(r["value"] - c["expected"]) <= c["tolerance"], (r["value"], c["expected"])
