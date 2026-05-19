import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer"))


def test_full_install_api_key(tmp_path):
    import install as ins
    config_file = tmp_path / ".claude.json"

    with patch("install.get_config_path", return_value=config_file), \
         patch("install.select_clients", return_value=["claude-code"]), \
         patch("install.prompt_auth", return_value=("mykey", None)), \
         patch("install.INSTALL_DIR", tmp_path), \
         patch("subprocess.run"):
        ins.run()

    result = json.loads(config_file.read_text())
    entry = result["mcpServers"]["arkham"]
    assert entry["env"]["ARKHAM_API_KEY"] == "mykey"
    assert entry["env"]["ARKHAM_PROVIDER"] == "arkham"


def test_full_install_cookie_runs_patchright(tmp_path):
    import install as ins
    config_file = tmp_path / ".claude.json"
    captured = []

    def fake_run(cmd, **kwargs):
        captured.append(cmd)

    with patch("install.get_config_path", return_value=config_file), \
         patch("install.select_clients", return_value=["claude-code"]), \
         patch("install.prompt_auth", return_value=(None, "mycookie")), \
         patch("install.INSTALL_DIR", tmp_path), \
         patch("subprocess.run", side_effect=fake_run):
        ins.run()

    assert any("patchright" in " ".join(c) for c in captured)


def test_full_install_multiple_clients(tmp_path):
    import install as ins
    paths = {
        "claude-code": tmp_path / ".claude.json",
        "cursor": tmp_path / ".cursor" / "mcp.json",
    }

    def fake_get_path(client, cwd=None):
        return paths[client]

    with patch("install.get_config_path", side_effect=fake_get_path), \
         patch("install.select_clients", return_value=["claude-code", "cursor"]), \
         patch("install.prompt_auth", return_value=("key", None)), \
         patch("install.INSTALL_DIR", tmp_path), \
         patch("subprocess.run"):
        ins.run()

    for path in paths.values():
        assert path.exists()
        result = json.loads(path.read_text())
        assert "arkham" in result["mcpServers"]
