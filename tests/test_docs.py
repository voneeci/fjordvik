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
