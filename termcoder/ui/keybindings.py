"""Keybindings for TermCoder prompt_toolkit interactive interface."""

from __future__ import annotations

import sys
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


def create_keybindings() -> KeyBindings:
    """Create key bindings with Windows clipboard integration and short commands."""
    kb = KeyBindings()

    @kb.add("c-v")
    def _handle_paste(event: KeyPressEvent) -> None:
        """Paste text from system clipboard at current cursor position."""
        text = ""
        if HAS_PYPERCLIP:
            try:
                text = pyperclip.paste()
            except Exception:
                text = ""

        if not text:
            # Fallback to prompt_toolkit clipboard
            data = event.app.clipboard.get_data()
            text = data.text if data else ""

        if text:
            event.current_buffer.insert_text(text)

    @kb.add("c-c")
    def _handle_ctrl_c(event: KeyPressEvent) -> None:
        """Copy selected text to clipboard, or reset the current line."""
        buf = event.current_buffer
        if buf.selection_state:
            # Copy active selection
            data = buf.copy_selection()
            if HAS_PYPERCLIP and data and data.text:
                try:
                    pyperclip.copy(data.text)
                except Exception:
                    pass
            buf.exit_selection()
        else:
            # Clear current input buffer
            buf.reset()

    @kb.add("escape", "enter")
    @kb.add("c-j")
    def _handle_multiline(event: KeyPressEvent) -> None:
        """Insert newline for multiline prompt."""
        event.current_buffer.insert_text("\n")

    @kb.add("c-l")
    def _handle_clear(event: KeyPressEvent) -> None:
        """Clear terminal screen."""
        event.app.renderer.clear()

    return kb
