import os
from pathlib import Path
from unittest.mock import patch

import pytest


def _import():
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer"))
    import config_paths
    return config_paths


def test_claude_code_linux():
    cp = _import()
    with patch("platform.system", return_value="Linux"):
        with patch.dict(os.environ, {}, clear=False):
            path = cp.get_config_path("claude-code")
    assert path == Path.home() / ".claude.json"


def test_claude_code_windows():
    cp = _import()
    with patch("platform.system", return_value="Windows"):
        with patch.dict(os.environ, {"APPDATA": "C:\\Users\\user\\AppData\\Roaming"}):
            path = cp.get_config_path("claude-code")
    assert path == Path("C:\\Users\\user\\AppData\\Roaming") / "Claude" / ".claude.json"


def test_claude_desktop_macos():
    cp = _import()
    with patch("platform.system", return_value="Darwin"):
        path = cp.get_config_path("claude-desktop")
    assert path == Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"


def test_claude_desktop_linux():
    cp = _import()
    with patch("platform.system", return_value="Linux"):
        path = cp.get_config_path("claude-desktop")
    assert path == Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def test_claude_desktop_windows():
    cp = _import()
    with patch("platform.system", return_value="Windows"):
        with patch.dict(os.environ, {"APPDATA": "C:\\Users\\user\\AppData\\Roaming"}):
            path = cp.get_config_path("claude-desktop")
    assert path == Path("C:\\Users\\user\\AppData\\Roaming") / "Claude" / "claude_desktop_config.json"


def test_cursor_linux():
    cp = _import()
    with patch("platform.system", return_value="Linux"):
        path = cp.get_config_path("cursor")
    assert path == Path.home() / ".cursor" / "mcp.json"


def test_cursor_windows():
    cp = _import()
    with patch("platform.system", return_value="Windows"):
        with patch.dict(os.environ, {"APPDATA": "C:\\Users\\user\\AppData\\Roaming"}):
            path = cp.get_config_path("cursor")
    assert path == Path("C:\\Users\\user\\AppData\\Roaming") / "Cursor" / "mcp.json"


def test_vscode_uses_cwd(tmp_path):
    cp = _import()
    path = cp.get_config_path("vscode", cwd=tmp_path)
    assert path == tmp_path / ".vscode" / "mcp.json"


def test_unknown_client_raises():
    cp = _import()
    with pytest.raises(ValueError, match="Unknown client"):
        cp.get_config_path("unknown-client")


def test_clients_list_contains_all():
    cp = _import()
    assert set(cp.CLIENTS) == {"claude-code", "claude-desktop", "cursor", "vscode"}
