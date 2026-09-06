"""Main CLI entrypoint and interactive REPL for TermCoder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.panel import Panel
from rich.table import Table

from termcoder import __version__
from termcoder.agent.loop import AgentLoop
from termcoder.agent.tools import ToolRegistry
from termcoder.config import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_HISTORY_FILE,
    Config,
    get_config,
)
from termcoder.context.indexer import CodebaseIndexer
from termcoder.llm.client import LLMClient
from termcoder.llm.models import ModelManager
from termcoder.llm.tracker import TokenTracker
from termcoder.plugins.manager import PluginManager
from termcoder.ui.completer import TermCoderCompleter
from termcoder.ui.keybindings import create_keybindings
from termcoder.ui.terminal import (
    confirm_command,
    console,
    print_banner,
    print_markdown,
    print_token_bar,
    print_tool_call,
    print_tool_result,
)

PROMPT_STYLE = Style.from_dict({
    "prompt": "ansicyan bold",
    "arrow": "ansigreen bold",
})


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="termcoder",
        description="TermCoder: Terminal AI Coding Assistant powered by NVIDIA NIM.",
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="Optional prompt to execute immediately (non-interactive mode).",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        help="Model ID to use for this session.",
    )
    parser.add_argument(
        "--key", "-k",
        type=str,
        help="Set or override the NVIDIA NIM API key.",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Auto-approve terminal commands without asking for confirmation.",
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"TermCoder {__version__}",
    )
    return parser.parse_args()


class TermCoderCLI:
    """Encapsulates the CLI session and REPL state."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.workspace_root = Path.cwd().resolve()
        self.config = get_config()

        # Apply CLI argument overrides
        if args.key:
            self.config.set_api_key(args.key, persist=True)
        if args.model:
            self.config.set_model(args.model, persist=False)
        if args.yes:
            self.config.auto_approve = True

        # Initialize components
        self.tracker = TokenTracker()
        self.client = LLMClient(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            model=self.config.model,
            tracker=self.tracker,
        )
        self.model_manager = ModelManager(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
        )

        self.tools = ToolRegistry(
            workspace_root=self.workspace_root,
            auto_approve=self.config.auto_approve,
            confirm_callback=confirm_command,
        )

        self.plugins = PluginManager(self.workspace_root)
        self.plugins.load_all_plugins(self.tools)

        self.agent = AgentLoop(
            llm_client=self.client,
            tool_registry=self.tools,
            on_tool_call=print_tool_call,
            on_tool_result=print_tool_result,
        )

        # Setup prompt_toolkit history
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.history = FileHistory(str(DEFAULT_HISTORY_FILE))

        # Setup prompt autocompleter
        self.completer = TermCoderCompleter(
            get_files=lambda: self.tools.indexer.get_relative_paths(),
            get_models=lambda: [m.id for m in self.model_manager.fetch_models()],
            get_custom_commands=lambda: list(self.plugins.commands.keys()),
        )

    def run(self) -> None:
        """Run interactive REPL or execute single query."""
        if self.args.query:
            prompt = " ".join(self.args.query)
            self._execute_single_prompt(prompt)
            return

        self._run_interactive_repl()

    def _execute_single_prompt(self, prompt: str) -> None:
        """Execute a one-off prompt passed via command line."""
        if not self.config.api_key:
            console.print("[bold red]Error:[/bold red] NVIDIA NIM API key is not configured.")
            console.print("Run [bold cyan]termcoder[/bold cyan] to enter interactive setup or set the [bold yellow]NVIDIA_API_KEY[/bold yellow] environment variable.")
            sys.exit(1)

        try:
            resp = self.agent.run_turn(prompt)
            print_markdown(resp)
            print_token_bar(self.tracker.format_summary_line())
        except Exception as e:
            console.print(f"[bold red]Execution error:[/bold red] {e}")
            sys.exit(1)

    def _run_interactive_repl(self) -> None:
        """Main interactive terminal loop."""
        print_banner(
            workspace_name=self.workspace_root.name,
            active_model=self.config.model,
            masked_key=self.config.masked_api_key(),
            auto_approve=self.tools.auto_approve,
        )

        if not self.config.api_key:
            console.print(
                Panel(
                    "[bold yellow]Welcome to TermCoder![/bold yellow]\n\n"
                    "No NVIDIA NIM API key was found.\n"
                    "You can get free API credits and keys at [bold cyan]https://build.nvidia.com[/bold cyan].\n\n"
                    "Please set your key now using: [bold green]/key nvapi-...[/bold green]",
                    title="NVIDIA NIM Setup",
                    border_style="yellow",
                )
            )

        session: PromptSession = PromptSession(
            history=self.history,
            completer=self.completer,
            key_bindings=create_keybindings(),
            style=PROMPT_STYLE,
        )

        while True:
            try:
                prompt_text = session.prompt(
                    [("class:arrow", "❯ "), ("class:prompt", "termcoder: ")]
                ).strip()

                if not prompt_text:
                    continue

                # Handle slash commands
                if prompt_text.startswith("/"):
                    should_continue = self._handle_slash_command(prompt_text)
                    if not should_continue:
                        break
                    continue

                # Normal agent prompt
                if not self.config.api_key:
                    console.print("[bold red]Please set your NVIDIA NIM API key first with:[/bold red] /key <your_key>")
                    continue

                console.print()
                with console.status("[bold green]Agent thinking & inspecting workspace...", spinner="dots"):
                    response_text = self.agent.run_turn(prompt_text)

                console.print()
                print_markdown(response_text)
                console.print()
                print_token_bar(self.tracker.format_summary_line())

            except KeyboardInterrupt:
                console.print("\n[dim]Action cancelled by user (Ctrl+C).[/dim]")
                continue
            except EOFError:
                console.print("\n[bold green]Goodbye![/bold green]")
                break
            except Exception as e:
                console.print(f"\n[bold red]Error:[/bold red] {e}")

    def _handle_slash_command(self, cmd_line: str) -> bool:
        """Handle slash command. Returns False if REPL should exit."""
        parts = cmd_line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in {"/exit", "/quit", "/q"}:
            console.print("[bold green]Goodbye![/bold green]")
            return False

        elif cmd == "/clear":
            console.clear()
            print_banner(
                workspace_name=self.workspace_root.name,
                active_model=self.config.model,
                masked_key=self.config.masked_api_key(),
                auto_approve=self.tools.auto_approve,
            )
            return True

        elif cmd == "/key":
            self._cmd_key(arg)
            return True

        elif cmd == "/models":
            self._cmd_models(arg)
            return True

        elif cmd == "/model":
            self._cmd_model(arg)
            return True

        elif cmd == "/tokens":
            self._cmd_tokens()
            return True

        elif cmd == "/auto":
            self.tools.auto_approve = not self.tools.auto_approve
            self.config.auto_approve = self.tools.auto_approve
            self.config.save()
            status = "[bold green]ON (commands run automatically)[/bold green]" if self.tools.auto_approve else "[bold yellow]OFF (prompts before running commands)[/bold yellow]"
            console.print(f"Auto-approve mode is now {status}")
            return True

        elif cmd == "/plugins":
            self.plugins.display_plugins_table(console)
            return True

        elif cmd.startswith("/plugin"):
            if arg.startswith("create"):
                plugin_name = arg.split(maxsplit=1)[1] if len(arg.split()) > 1 else "my_plugin"
                path = self.plugins.create_plugin_scaffold(plugin_name)
                console.print(f"[bold green]Plugin scaffold created at:[/bold green] {path}")
            else:
                self.plugins.display_plugins_table(console)
            return True

        elif cmd == "/git":
            self._cmd_git(arg)
            return True

        elif cmd == "/help":
            self._cmd_help()
            return True

        # Check plugin custom commands
        clean_cmd = cmd.lstrip("/")
        custom_handler = self.plugins.get_command(clean_cmd)
        if custom_handler:
            try:
                custom_handler(arg.split() if arg else [])
            except Exception as e:
                console.print(f"[bold red]Plugin command error:[/bold red] {e}")
            return True

        console.print(f"[bold red]Unknown command:[/bold red] {cmd}. Type [bold cyan]/help[/bold cyan] for available commands.")
        return True

    def _cmd_key(self, new_key: str) -> None:
        """Inspect or update the NVIDIA NIM API key at runtime."""
        if not new_key:
            console.print(f"[bold]Active API Key:[/bold] [yellow]{self.config.masked_api_key()}[/yellow]")
            console.print("To update, enter: [bold cyan]/key nvapi-...[/bold cyan] or input below:")
            try:
                entered = console.input("[bold]Enter new API key (or Enter to cancel): [/bold]").strip()
                if not entered:
                    return
                new_key = entered
            except (KeyboardInterrupt, EOFError):
                return

        # Validate with NVIDIA NIM endpoint
        with console.status("[bold green]Validating key with NVIDIA NIM...", spinner="dots"):
            valid, msg = self.model_manager.validate_api_key(new_key)

        if valid:
            self.config.set_api_key(new_key, persist=True)
            self.client.update_credentials(new_key)
            self.model_manager.update_credentials(new_key)
            console.print(f"[bold green]✓ API key updated and verified successfully![/bold green] Key saved to {DEFAULT_CONFIG_DIR / 'config.json'}")
            console.print(f"Active Key: [yellow]{self.config.masked_api_key()}[/yellow]")
        else:
            console.print(f"[bold yellow]Warning:[/bold yellow] {msg}")
            # Ask if user wants to save anyway
            try:
                save_anyway = console.input("[bold]Save this key anyway? (y/n): [/bold]").strip().lower()
                if save_anyway in {"y", "yes"}:
                    self.config.set_api_key(new_key, persist=True)
                    self.client.update_credentials(new_key)
                    self.model_manager.update_credentials(new_key)
                    console.print(f"[bold green]API key saved.[/bold green] Active Key: [yellow]{self.config.masked_api_key()}[/yellow]")
            except (KeyboardInterrupt, EOFError):
                pass

    def _cmd_models(self, query: str) -> None:
        """Fetch models dynamically from NVIDIA NIM and display table."""
        with console.status("[bold green]Fetching models from NVIDIA NIM...", spinner="dots"):
            models = self.model_manager.fetch_models(query=query, force_refresh=True)

        if not models:
            console.print(f"[yellow]No models found matching '{query}'.[/yellow]")
            return

        table = Table(
            title=f"NVIDIA NIM Available Models ({len(models)} total)",
            border_style="green",
            expand=True,
        )
        table.add_column("Model ID", style="bold cyan", ratio=3)
        table.add_column("Provider / Owner", style="magenta", ratio=1)
        table.add_column("Status / Tier", style="bold green", ratio=1)

        for m in models[:40]:
            is_active = (m.id == self.config.model)
            model_display = f"★ {m.id} (active)" if is_active else m.id
            style = "bold yellow" if is_active else ("green" if m.is_recommended else "white")
            tier_badge = "[bold green]Free / Available[/bold green]" if m.is_recommended else "Available"
            table.add_row(model_display, m.owner or "nvidia", tier_badge, style=style)

        console.print(table)
        if len(models) > 40:
            console.print(f"[dim]Showing top 40 of {len(models)} models. Filter with `/models <name>`.[/dim]")
        console.print("[dim]Switch active model with:[/dim] [bold cyan]/model <model_id>[/bold cyan]")

    def _cmd_model(self, model_name: str) -> None:
        """Switch active AI model."""
        if not model_name:
            console.print(f"Current active model: [bold magenta]{self.config.model}[/bold magenta]")
            console.print("To change, type: [bold cyan]/model <model_id>[/bold cyan] or browse with [bold cyan]/models[/bold cyan]")
            return

        self.config.set_model(model_name, persist=True)
        self.client.set_model(model_name)
        console.print(f"[bold green]✓ Switched active model to:[/bold green] [bold magenta]{model_name}[/bold magenta]")

    def _cmd_tokens(self) -> None:
        """Display detailed token usage metrics."""
        table = Table(title="Token Usage Breakdown", border_style="cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Count", justify="right", style="green")

        latest = self.tracker.latest_turn()
        table.add_row("Last Turn Prompt Tokens", f"{latest.prompt_tokens:,}")
        table.add_row("Last Turn Completion Tokens", f"{latest.completion_tokens:,}")
        table.add_row("Last Turn Cached Tokens", f"{latest.cached_tokens:,}")
        table.add_row("Last Turn Total Tokens", f"{latest.total_tokens:,}")
        table.add_section()
        table.add_row("Session Turns", f"{self.tracker.session_turns:,}")
        table.add_row("Session Total Input Tokens", f"{self.tracker.session_prompt_tokens:,}")
        table.add_row("Session Total Output Tokens", f"{self.tracker.session_completion_tokens:,}")
        table.add_row("Session Cumulative Tokens", f"{self.tracker.session_total_tokens:,}")

        console.print(table)

    def _cmd_git(self, arg: str) -> None:
        """Quick git helper."""
        if not arg or arg == "status":
            out = self.tools.execute_tool("git_status", {})
            print_tool_result("git_status", out)
        elif arg == "diff":
            out = self.tools.execute_tool("git_diff", {"staged": False})
            print_tool_result("git_diff", out)
        else:
            # Let agent handle complex git command
            self.agent.run_turn(f"Handle git: {arg}")

    def _cmd_help(self) -> None:
        """Display help panel with commands, shortcuts, and workflows."""
        help_text = """[bold cyan]Slash Commands:[/bold cyan]
  • [bold]/key [new_key][/bold]     View or update NVIDIA NIM API key at runtime
  • [bold]/models [filter][/bold]   Fetch & list available free models from NVIDIA NIM
  • [bold]/model <id>[/bold]       Switch the active model (e.g. meta/llama-3.3-70b-instruct)
  • [bold]/tokens[/bold]           Display token usage metrics for this turn and session
  • [bold]/auto[/bold]             Toggle auto-approval for shell commands ON / OFF
  • [bold]/git [status|diff][/bold] Quick git status and diff preview
  • [bold]/plugins[/bold]          List installed plugins and their commands
  • [bold]/plugin create <n>[/bold] Create a new custom plugin boilerplate
  • [bold]/sysinfo[/bold]          Display system hardware, Python, and disk diagnostics
  • [bold]/clear[/bold]            Clear terminal screen
  • [bold]/exit[/bold]             Exit TermCoder

[bold cyan]Shortcuts & Terminal Controls:[/bold cyan]
  • [bold]Ctrl+V[/bold]            Paste text/code from Windows clipboard
  • [bold]Ctrl+C[/bold]            Copy selected text or cancel current input/running agent
  • [bold]Tab[/bold]               Autocomplete slash commands, @files, and model names
  • [bold]Esc + Enter[/bold]      Insert newline for multi-line prompts
  • [bold]Up / Down[/bold]        Navigate through prompt command history

[bold cyan]Context Mentions & Natural Language Examples:[/bold cyan]
  • [bold]@file_path[/bold]         Include specific file contents directly into prompt
  • [dim]"Explain the function calculate_tokens in tracker.py"[/dim]
  • [dim]"Run tests for tests/test_agent.py and fix any failures"[/dim]
  • [dim]"Stage all modified files and commit with a good conventional commit message"[/dim]
"""
        console.print(Panel(help_text, title="TermCoder Help & Shortcuts", border_style="cyan"))


def main() -> None:
    """Main CLI entrypoint."""
    args = parse_args()
    cli = TermCoderCLI(args)
    cli.run()


if __name__ == "__main__":
    main()
