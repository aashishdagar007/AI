"""Rich terminal interface and formatting components for TermCoder."""

from __future__ import annotations

import difflib
from typing import Optional
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

console = Console()


def print_banner(
    workspace_name: str,
    active_model: str,
    masked_key: str,
    auto_approve: bool = False,
) -> None:
    """Render startup banner with session metadata and tips."""
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(justify="left", ratio=2)
    grid.add_column(justify="right", ratio=1)

    left_text = Text()
    left_text.append("⚡ TermCoder ", style="bold green")
    left_text.append("v0.1.0\n", style="dim")
    left_text.append("• Workspace: ", style="bold")
    left_text.append(f"{workspace_name}\n", style="cyan")
    left_text.append("• Active Model: ", style="bold")
    left_text.append(f"{active_model}\n", style="magenta")
    left_text.append("• NVIDIA NIM Key: ", style="bold")
    left_text.append(f"{masked_key}\n", style="yellow")
    left_text.append("• Auto-Approve: ", style="bold")
    left_text.append("ON" if auto_approve else "OFF (asks before running commands)", style="green" if auto_approve else "dim")

    right_text = Text()
    right_text.append("Shortcuts & Tips\n", style="bold underline")
    right_text.append("• Ctrl+V: Paste from clipboard\n", style="dim")
    right_text.append("• Ctrl+C: Cancel / Copy\n", style="dim")
    right_text.append("• Esc+Enter: New line\n", style="dim")
    right_text.append("• /key: Change API key\n", style="dim")
    right_text.append("• /models: Browse models\n", style="dim")
    right_text.append("• /help: Show all commands\n", style="dim")

    grid.add_row(left_text, right_text)

    banner_panel = Panel(
        grid,
        title="[bold green]TermCoder: Terminal AI Coding Assistant[/bold green]",
        subtitle="[dim]Powered by NVIDIA NIM • Press Tab for autocompletion[/dim]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(banner_panel)


def print_token_bar(token_summary_str: str) -> None:
    """Print the token usage status line."""
    console.print(f"[dim]{token_summary_str}[/dim]\n")


def print_tool_call(tool_name: str, args: dict) -> None:
    """Display an invocation badge for a tool."""
    summary = ", ".join(f"{k}={repr(v)[:50]}" for k, v in args.items())
    console.print(f"\n[bold yellow]🛠  Calling Tool:[/bold yellow] [bold cyan]{tool_name}[/bold cyan] [dim]({summary})[/dim]")


def print_tool_result(tool_name: str, result: str, max_lines: int = 15) -> None:
    """Display the result returned by a tool."""
    lines = result.splitlines()
    if len(lines) > max_lines:
        display_text = "\n".join(lines[:max_lines]) + f"\n... [{len(lines) - max_lines} more lines]"
    else:
        display_text = result

    border_color = "red" if "error" in tool_name.lower() or "error" in result.lower()[:30] else "green"
    console.print(
        Panel(
            display_text,
            title=f"Tool Output: {tool_name}",
            border_style=border_color,
            padding=(0, 1),
        )
    )


def print_markdown(content: str) -> None:
    """Render formatted markdown to console."""
    md = Markdown(content)
    console.print(md)


def print_diff(filename: str, old_code: str, new_code: str) -> None:
    """Render syntax-highlighted unified diff for code changes."""
    diff_lines = list(
        difflib.unified_diff(
            old_code.splitlines(keepends=True),
            new_code.splitlines(keepends=True),
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
        )
    )
    if not diff_lines:
        return

    diff_text = "".join(diff_lines)
    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
    console.print(Panel(syntax, title=f"Changes: {filename}", border_style="blue"))


def confirm_command(command: str) -> bool:
    """
    Prompt user for confirmation before executing an arbitrary terminal command.
    Returns True if approved, False otherwise.
    """
    console.print(
        Panel(
            f"[bold yellow]The agent wants to execute this terminal command:[/bold yellow]\n\n"
            f"[bold cyan]{command}[/bold cyan]",
            title="Command Approval Required",
            border_style="yellow",
        )
    )
    try:
        choice = console.input("[bold]Allow execution? ([green]y[/green]/[red]n[/red]): [/bold]").strip().lower()
        return choice in {"y", "yes"}
    except (KeyboardInterrupt, EOFError):
        return False
