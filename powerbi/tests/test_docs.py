"""Generated documents are up to date with the model."""

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_data_dictionary_matches_the_model(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "build_data_dictionary", REPO / "scripts" / "build_data_dictionary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "OUT", tmp_path / "data-dictionary.md")
    module.main()
    committed = (REPO / "docs" / "data-dictionary.md").read_bytes()
    assert (tmp_path / "data-dictionary.md").read_bytes() == committed, \
        "docs/data-dictionary.md is out of date: run python scripts/build_data_dictionary.py"


def test_measure_guide_matches_the_model_and_reports(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "build_measure_guide", REPO / "scripts" / "build_measure_guide.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "OUT", tmp_path / "measure-guide.md")
    module.main()
    committed = (REPO / "docs" / "measure-guide.md").read_bytes()
    assert (tmp_path / "measure-guide.md").read_bytes() == committed,         "docs/measure-guide.md is out of date: run python scripts/build_measure_guide.py"


def test_every_measure_has_an_example_value():
    """Each measure in the guide carries a value read from the live model (--capture)."""
    import json
    spec = importlib.util.spec_from_file_location(
        "build_measure_guide", REPO / "scripts" / "build_measure_guide.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    examples = json.loads((REPO / "docs" / "measure-examples.json").read_text(encoding="utf-8"))
    names = {m["name"] for m in module.measures()}
    assert set(examples) == names, set(examples) ^ names
    assert all(e["value"] is not None for e in examples.values())
