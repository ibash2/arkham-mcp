import os
import platform
from pathlib import Path

CLIENTS = ["claude-code", "claude-desktop", "cursor", "vscode"]

CLIENT_LABELS = {
    "claude-code": "Claude Code (CLI)",
    "claude-desktop": "Claude Desktop",
    "cursor": "Cursor",
    "vscode": "VS Code",
}


def get_config_path(client: str, cwd: Path | None = None) -> Path:
    system = platform.system()

    if client == "claude-code":
        if system == "Windows":
            return Path(os.environ["APPDATA"]) / "Claude" / ".claude.json"
        return Path.home() / ".claude.json"

    if client == "claude-desktop":
        if system == "Darwin":
            return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        if system == "Windows":
            return Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    if client == "cursor":
        if system == "Windows":
            return Path(os.environ["APPDATA"]) / "Cursor" / "mcp.json"
        return Path.home() / ".cursor" / "mcp.json"

    if client == "vscode":
        base = cwd or Path.cwd()
        return base / ".vscode" / "mcp.json"

    raise ValueError(f"Unknown client: {client!r}")
