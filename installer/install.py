#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

# When invoked via `curl | bash`, bash's stdin is the pipe, not the terminal.
# Reconnect stdin to /dev/tty so interactive prompts work.
try:
    if not sys.stdin.isatty():
        sys.stdin = open("/dev/tty")
except OSError:
    pass

sys.path.insert(0, str(Path(__file__).parent))

from config_paths import CLIENTS, CLIENT_LABELS, get_config_path
from config_writer import merge_arkham_entry
from mcp_entry import build_mcp_entry

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()

INSTALL_DIR = Path(__file__).parent.parent


def select_clients() -> list[str]:
    console.print("\n[bold]Which clients do you want to configure?[/bold]")
    for i, key in enumerate(CLIENTS, 1):
        console.print(f"  [cyan]{i}[/cyan]. {CLIENT_LABELS[key]}")
    console.print()

    while True:
        raw = Prompt.ask("Enter numbers separated by commas (e.g. [cyan]1,3[/cyan])")
        try:
            indices = [int(x.strip()) for x in raw.split(",")]
            selected = [CLIENTS[i - 1] for i in indices if 1 <= i <= len(CLIENTS)]
            if selected:
                return selected
        except (ValueError, IndexError):
            pass
        console.print("[red]Invalid input — try again[/red]")


def prompt_auth() -> tuple[str | None, str | None]:
    console.print("\n[bold]Authentication[/bold] [dim](optional — only needed for your account data)[/dim]")
    console.print("  [cyan]1[/cyan]. Guest     [dim](full public access)[/dim]")
    console.print("  [cyan]2[/cyan]. API key")
    console.print("  [cyan]3[/cyan]. Cookie    [dim](your account)[/dim]")
    console.print()

    choice = Prompt.ask("Choose", choices=["1", "2", "3"], default="1")

    if choice == "2":
        key = Prompt.ask("ARKHAM_API_KEY", password=True)
        return key, None
    if choice == "3":
        cookie = Prompt.ask("ARKHAM_COOKIE value", password=True)
        return None, cookie
    return None, None


def run() -> None:
    console.rule("[bold blue]Arkham MCP Installer[/bold blue]")

    clients = select_clients()
    api_key, cookie = prompt_auth()
    entry = build_mcp_entry(INSTALL_DIR, api_key, cookie)

    console.print()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Client")
    table.add_column("Config path")
    table.add_column("Status")

    for client in clients:
        path = get_config_path(client)
        try:
            merge_arkham_entry(path, entry)
            table.add_row(CLIENT_LABELS[client], str(path), "[green]✓ configured[/green]")
        except Exception as exc:
            table.add_row(CLIENT_LABELS[client], str(path), f"[red]✗ {exc}[/red]")

    console.print(table)

    if cookie:
        console.print("\n[bold]Installing Chromium for playwright mode…[/bold]")
        result = subprocess.run(
            ["uv", "run", "patchright", "install", "chromium"],
            cwd=INSTALL_DIR,
        )
        if result is not None and result.returncode != 0:
            console.print("[yellow]⚠ Chromium install failed. Run manually:[/yellow]")
            console.print(f"  cd {INSTALL_DIR} && uv run patchright install chromium")

    console.print("\n[bold green]✓ Done! Restart your AI client to apply changes.[/bold green]")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        sys.exit(1)
