import json
import os
from pathlib import Path
from unittest.mock import patch
import sys
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer"))
import config_writer as cw


def test_creates_file_from_scratch(tmp_path):
    target = tmp_path / "subdir" / "config.json"
    entry = {"type": "stdio", "command": "uv"}

    cw.merge_arkham_entry(target, entry)

    result = json.loads(target.read_text())
    assert result == {"mcpServers": {"arkham": entry}}


def test_merges_into_existing_config(tmp_path):
    target = tmp_path / "config.json"
    existing = {"theme": "dark", "mcpServers": {"other": {"command": "npx"}}}
    target.write_text(json.dumps(existing))
    entry = {"type": "stdio", "command": "uv"}

    cw.merge_arkham_entry(target, entry)

    result = json.loads(target.read_text())
    assert result["theme"] == "dark"
    assert result["mcpServers"]["other"] == {"command": "npx"}
    assert result["mcpServers"]["arkham"] == entry


def test_adds_mcp_servers_key_if_missing(tmp_path):
    target = tmp_path / "config.json"
    target.write_text(json.dumps({"theme": "dark"}))
    entry = {"type": "stdio", "command": "uv"}

    cw.merge_arkham_entry(target, entry)

    result = json.loads(target.read_text())
    assert "mcpServers" in result
    assert result["mcpServers"]["arkham"] == entry


def test_overwrites_existing_arkham_entry(tmp_path):
    target = tmp_path / "config.json"
    old_entry = {"command": "old"}
    target.write_text(json.dumps({"mcpServers": {"arkham": old_entry}}))
    new_entry = {"type": "stdio", "command": "uv"}

    cw.merge_arkham_entry(target, new_entry)

    result = json.loads(target.read_text())
    assert result["mcpServers"]["arkham"] == new_entry


def test_write_is_atomic(tmp_path):
    target = tmp_path / "config.json"
    entry = {"type": "stdio"}
    calls = []
    real_replace = os.replace

    def spy_replace(src, dst):
        calls.append((src, dst))
        real_replace(src, dst)

    with patch("config_writer.os.replace", side_effect=spy_replace):
        cw.merge_arkham_entry(target, entry)

    assert len(calls) == 1
    assert Path(calls[0][1]) == target


def test_no_temp_file_left_after_write(tmp_path):
    target = tmp_path / "config.json"
    cw.merge_arkham_entry(target, {"command": "uv"})

    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []
