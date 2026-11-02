"""The service documents: one manual per product group with equipment, numbered
sections, and part numbers and alarm limits that match the data (added 2 November 2026)."""

import hashlib
import json
import re

import pytest

from fjordvik_data import config as c
from fjordvik_data.corpus import GROUPS

PART_ID = re.compile(r"\b[A-Z]{2}-[A-Z]{2}-[A-Z0-9]{2}\b")


@pytest.fixture(scope="module")
def corpus(data_dir):
    folder = data_dir.parent / "corpus"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    return folder, manifest


def test_one_manual_per_group_plus_terms_and_warranty(corpus):
    folder, manifest = corpus
    expected = {GROUPS[g][1] for g in GROUPS} | {"service-terms.md", "warranty-policy.md"}
    assert set(manifest["documents"]) == expected
    assert {p.name for p in folder.glob("*.md")} == expected
    assert len(GROUPS) == 8
    for name, info in manifest["documents"].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == info["sha256"], name


def test_sections_are_numbered_in_order(corpus):
    folder, manifest = corpus
    for name in manifest["documents"]:
        lines = (folder / name).read_text(encoding="utf-8").splitlines()
        sections = [int(m.group(1)) for line in lines if (m := re.match(r"## (\d+)\. ", line))]
        assert sections == list(range(1, len(sections) + 1)), name
        current = 0
        for line in lines:
            if m := re.match(r"## (\d+)\. ", line):
                current, sub = int(m.group(1)), 0
            elif m := re.match(r"### (\d+)\.(\d+) ", line):
                assert int(m.group(1)) == current, (name, line)
                sub += 1
                assert int(m.group(2)) == sub, (name, line)


def test_every_part_number_exists_and_fits_the_manual(tables, corpus):
    folder, _ = corpus
    fits = {(r["part_id"], r["product_group"]) for r in tables["bridge_part_compatibility"]}
    parts = {r["part_id"] for r in tables["dim_part"]}
    for group, (_code, name, *_rest) in GROUPS.items():
        text = (folder / name).read_text(encoding="utf-8")
        cited = set(PART_ID.findall(text))
        assert cited, name
        for part in cited:
            assert part in parts and (part, group) in fits, (name, part)


def test_alarm_limits_match_the_settings(corpus):
    folder, _ = corpus
    for group, (vib_alert, vib_alarm, t_alert, t_alarm) in c.ALARM_LIMITS.items():
        text = (folder / GROUPS[group][1]).read_text(encoding="utf-8")
        assert f"| Vibration (mm/s RMS) | {vib_alert} | {vib_alarm} |" in text, group
        assert f"| Bearing temperature (C) | {t_alert} | {t_alarm} |" in text, group


def test_every_document_says_it_is_synthetic(corpus):
    folder, manifest = corpus
    for name in manifest["documents"]:
        assert "Synthetic document for a portfolio project" in (folder / name).read_text(encoding="utf-8")
