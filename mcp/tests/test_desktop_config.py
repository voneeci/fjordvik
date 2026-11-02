"""The Claude Desktop script writes the configuration file Desktop actually reads."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "add_to_claude_desktop.py"


def config_path(monkeypatch, local: Path, roaming: Path) -> Path:
    """Load the script with LOCALAPPDATA and APPDATA pointing at temporary folders."""
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    monkeypatch.setenv("APPDATA", str(roaming))
    spec = importlib.util.spec_from_file_location("add_to_claude_desktop", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.config_path()


def store_folders(local: Path) -> tuple[Path, Path]:
    claude_data = local / "Claude-Data" / "claude_abc123"
    package = local / "Packages" / "Claude_abc123" / "LocalCache" / "Roaming" / "Claude"
    claude_data.mkdir(parents=True)
    package.mkdir(parents=True)
    return claude_data, package


def test_claude_data_file_wins_when_it_exists(monkeypatch, tmp_path):
    claude_data, _package = store_folders(tmp_path / "local")
    (claude_data / "claude_desktop_config.json").write_text("{}", encoding="utf-8")
    found = config_path(monkeypatch, tmp_path / "local", tmp_path / "roaming")
    assert found == claude_data / "claude_desktop_config.json"


def test_package_folder_is_used_when_claude_data_has_no_config(monkeypatch, tmp_path):
    _claude_data, package = store_folders(tmp_path / "local")
    found = config_path(monkeypatch, tmp_path / "local", tmp_path / "roaming")
    assert found == package / "claude_desktop_config.json"


def test_installer_folder_is_the_last_resort(monkeypatch, tmp_path):
    (tmp_path / "local").mkdir()
    found = config_path(monkeypatch, tmp_path / "local", tmp_path / "roaming")
    assert found == tmp_path / "roaming" / "Claude" / "claude_desktop_config.json"
