"""Prompt autocompleter for slash commands, @files, and models."""

from __future__ import annotations

import re
from typing import Callable, Iterable, List, Optional
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document


DEFAULT_SLASH_COMMANDS = [
    ("/help", "Show available commands, workflows, and shortcuts"),
    ("/key", "View or modify the active NVIDIA NIM API key"),
    ("/models", "Fetch and display available models from NVIDIA NIM"),
    ("/model", "Switch active AI model (e.g. /model meta/llama-3.3-70b-instruct)"),
    ("/tokens", "Display live session and turn token usage statistics"),
    ("/git", "Quick git status and workflow helper"),
    ("/plugins", "List active plugins and their custom commands"),
    ("/plugin create", "Scaffold a new custom plugin"),
    ("/auto", "Toggle auto-approval mode for running terminal commands"),
    ("/sysinfo", "Display system hardware, Python, and OS diagnostics"),
    ("/clear", "Clear terminal screen"),
    ("/exit", "Exit TermCoder"),
]


class TermCoderCompleter(Completer):
    """Dynamic autocompleter for TermCoder interactive prompt."""

    def __init__(
        self,
        get_files: Optional[Callable[[], List[str]]] = None,
        get_models: Optional[Callable[[], List[str]]] = None,
        get_custom_commands: Optional[Callable[[], List[str]]] = None,
    ) -> None:
        self.get_files = get_files
        self.get_models = get_models
        self.get_custom_commands = get_custom_commands

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        text_before_cursor = document.text_before_cursor
        word_before_cursor = document.get_word_before_cursor(WORD=True)

        # 1. Slash commands at start of prompt
        if text_before_cursor.startswith("/"):
            # Check if typing `/model `
            if text_before_cursor.startswith("/model "):
                prefix = text_before_cursor[7:].strip()
                models = self.get_models() if self.get_models else []
                for m in models:
                    if prefix.lower() in m.lower():
                        yield Completion(m, start_position=-len(prefix), display=m, display_meta="model")
                return

            prefix = text_before_cursor
            for cmd, desc in DEFAULT_SLASH_COMMANDS:
                if cmd.lower().startswith(prefix.lower()):
                    yield Completion(
                        cmd,
                        start_position=-len(prefix),
                        display=cmd,
                        display_meta=desc,
                    )

            if self.get_custom_commands:
                for custom_cmd in self.get_custom_commands():
                    full_cmd = f"/{custom_cmd.lstrip('/')}"
                    if full_cmd.lower().startswith(prefix.lower()):
                        yield Completion(
                            full_cmd,
                            start_position=-len(prefix),
                            display=full_cmd,
                            display_meta="custom plugin command",
                        )
            return

        # 2. @file mentions anywhere in the text
        at_match = re.search(r"@([a-zA-Z0-9_\-\.\/\\]*)$", text_before_cursor)
        if at_match:
            file_prefix = at_match.group(1).lower()
            files = self.get_files() if self.get_files else []
            for f in files:
                if file_prefix in f.lower():
                    # Replace just the prefix after @
                    yield Completion(
                        f,
                        start_position=-len(file_prefix),
                        display=f"@{f}",
                        display_meta="file",
                    )
            return
