import os
from pathlib import Path
from unittest.mock import patch

import pytest


def test_claude_code_linux(cp):
    with patch("platform.system", return_value="Linux"):
        path = cp.get_config_path("claude-code")
    assert path == Path.home() / ".claude.json"


def test_claude_code_windows(cp):
    with patch("platform.system", return_value="Windows"):
        with patch.dict(os.environ, {"APPDATA": "C:\\Users\\user\\AppData\\Roaming"}):
            path = cp.get_config_path("claude-code")
    assert path == Path("C:\\Users\\user\\AppData\\Roaming") / "Claude" / ".claude.json"


def test_claude_desktop_macos(cp):
    with patch("platform.system", return_value="Darwin"):
        path = cp.get_config_path("claude-desktop")
    assert path == Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"


def test_claude_desktop_linux(cp):
    with patch("platform.system", return_value="Linux"):
        path = cp.get_config_path("claude-desktop")
    assert path == Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def test_claude_desktop_windows(cp):
    with patch("platform.system", return_value="Windows"):
        with patch.dict(os.environ, {"APPDATA": "C:\\Users\\user\\AppData\\Roaming"}):
            path = cp.get_config_path("claude-desktop")
    assert path == Path("C:\\Users\\user\\AppData\\Roaming") / "Claude" / "claude_desktop_config.json"


def test_cursor_linux(cp):
    with patch("platform.system", return_value="Linux"):
        path = cp.get_config_path("cursor")
    assert path == Path.home() / ".cursor" / "mcp.json"


def test_cursor_windows(cp):
    with patch("platform.system", return_value="Windows"):
        with patch.dict(os.environ, {"APPDATA": "C:\\Users\\user\\AppData\\Roaming"}):
            path = cp.get_config_path("cursor")
    assert path == Path("C:\\Users\\user\\AppData\\Roaming") / "Cursor" / "mcp.json"


def test_vscode_uses_cwd(cp, tmp_path):
    path = cp.get_config_path("vscode", cwd=tmp_path)
    assert path == tmp_path / ".vscode" / "mcp.json"


def test_vscode_no_cwd(cp):
    path = cp.get_config_path("vscode")
    assert path.name == "mcp.json"
    assert path.parent.name == ".vscode"


def test_unknown_client_raises(cp):
    with pytest.raises(ValueError, match="Unknown client"):
        cp.get_config_path("unknown-client")


def test_clients_list_contains_all(cp):
    assert set(cp.CLIENTS) == {"claude-code", "claude-desktop", "cursor", "vscode"}
    assert set(cp.CLIENT_LABELS) == {"claude-code", "claude-desktop", "cursor", "vscode"}
