from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer"))
import mcp_entry as me


def test_api_key_mode(tmp_path):
    entry = me.build_mcp_entry(tmp_path, api_key="mykey", cookie=None)
    assert entry["type"] == "stdio"
    assert entry["command"] == "uv"
    assert entry["args"] == ["--directory", str(tmp_path), "run", "arkham-mcp"]
    assert entry["env"]["ARKHAM_API_KEY"] == "mykey"
    assert entry["env"]["ARKHAM_PROVIDER"] == "arkham"
    assert entry["env"]["ARKHAM_BASE_URL"] == "https://api.arkm.com"
    assert "ARKHAM_COOKIE" not in entry["env"]


def test_cookie_mode(tmp_path):
    entry = me.build_mcp_entry(tmp_path, api_key=None, cookie="mytoken")
    assert entry["env"]["ARKHAM_COOKIE"] == "mytoken"
    assert entry["env"]["ARKHAM_PROVIDER"] == "playwright"
    assert "ARKHAM_API_KEY" not in entry["env"]


def test_guest_mode(tmp_path):
    entry = me.build_mcp_entry(tmp_path, api_key=None, cookie=None)
    assert "ARKHAM_API_KEY" not in entry["env"]
    assert "ARKHAM_COOKIE" not in entry["env"]
    assert entry["env"]["ARKHAM_PROVIDER"] == "arkham"


def test_install_dir_in_args(tmp_path):
    entry = me.build_mcp_entry(tmp_path, api_key="k", cookie=None)
    assert str(tmp_path) in entry["args"]
