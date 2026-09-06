"""Base class and interface for TermCoder plugins."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from termcoder.agent.tools import ToolRegistry


class BasePlugin:
    """Base class for all TermCoder plugins."""

    name: str = "base_plugin"
    description: str = "Base plugin description"
    version: str = "0.1.0"

    def register_commands(self) -> Dict[str, Callable[[List[str]], None]]:
        """
        Return custom slash commands to add to the CLI REPL.
        Example: {"docker": self.handle_docker_command}
        """
        return {}

    def register_tools(self, registry: "ToolRegistry") -> None:
        """
        Register custom tools for the LLM agent.
        Example: registry.register_custom_tool("deploy_app", ...)
        """
        pass

    def on_session_start(self, context: dict) -> None:
        """Called when a TermCoder session starts."""
        pass
