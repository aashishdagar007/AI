"""Plugin manager for discovering, loading, and managing TermCoder plugins."""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from rich.console import Console
from rich.table import Table

from termcoder.config import DEFAULT_PLUGINS_DIR
from termcoder.plugins.base import BasePlugin
from termcoder.plugins.builtin.system_info import SystemInfoPlugin

if TYPE_CHECKING:
    from termcoder.agent.tools import ToolRegistry


class PluginManager:
    """Manages discovery and lifecycle of TermCoder plugins."""

    def __init__(self, workspace_root: Path | str = ".") -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.plugins: Dict[str, BasePlugin] = {}
        self.commands: Dict[str, Callable[[List[str]], None]] = {}

    def load_all_plugins(self, tool_registry: Optional["ToolRegistry"] = None) -> None:
        """Discover and load builtin, global, and workspace plugins."""
        # 1. Load built-ins
        self._register_plugin_instance(SystemInfoPlugin(), tool_registry)

        # 2. Load global plugins (~/.termcoder/plugins)
        self._load_from_directory(DEFAULT_PLUGINS_DIR, tool_registry)

        # 3. Load workspace plugins (./.termcoder/plugins)
        workspace_plugins = self.workspace_root / ".termcoder" / "plugins"
        self._load_from_directory(workspace_plugins, tool_registry)

    def _load_from_directory(self, directory: Path, tool_registry: Optional["ToolRegistry"]) -> None:
        """Scan a directory for .py plugin files."""
        if not directory.exists() or not directory.is_dir():
            return

        for py_file in directory.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            self._load_plugin_file(py_file, tool_registry)

    def _load_plugin_file(self, file_path: Path, tool_registry: Optional["ToolRegistry"]) -> None:
        """Dynamically import a Python file and instantiate BasePlugin subclasses."""
        try:
            module_name = f"termcoder_plugin_{file_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, BasePlugin) and obj is not BasePlugin:
                    instance = obj()
                    self._register_plugin_instance(instance, tool_registry)
        except Exception as e:
            # Silently skip broken plugins or print to debug log
            pass

    def _register_plugin_instance(self, plugin: BasePlugin, tool_registry: Optional["ToolRegistry"]) -> None:
        """Register a single plugin instance, its commands, and its tools."""
        self.plugins[plugin.name] = plugin

        # Register slash commands
        cmds = plugin.register_commands()
        for cmd_name, handler in cmds.items():
            self.commands[cmd_name.lower().lstrip("/")] = handler

        # Register LLM tools if registry provided
        if tool_registry:
            plugin.register_tools(tool_registry)

    def get_command(self, name: str) -> Optional[Callable[[List[str]], None]]:
        """Look up a command handler registered by a plugin."""
        return self.commands.get(name.lower().lstrip("/"))

    def display_plugins_table(self, console: Console) -> None:
        """Render a formatted table of loaded plugins."""
        table = Table(title="Installed Plugins", border_style="cyan")
        table.add_column("Plugin Name", style="bold green")
        table.add_column("Version", style="dim")
        table.add_column("Description", style="white")
        table.add_column("Commands", style="yellow")

        for name, p in sorted(self.plugins.items()):
            cmds = ", ".join(f"/{c}" for c in p.register_commands().keys()) or "(none)"
            table.add_row(p.name, p.version, p.description, cmds)

        console.print(table)

    @staticmethod
    def create_plugin_scaffold(name: str, target_dir: Optional[Path] = None) -> Path:
        """Generate boilerplate code for a new custom plugin."""
        dest_dir = target_dir or (DEFAULT_PLUGINS_DIR)
        dest_dir.mkdir(parents=True, exist_ok=True)
        file_path = dest_dir / f"{name.lower().replace('-', '_')}.py"

        template = f'''"""Custom plugin: {name}"""

from typing import Dict, Callable, List
from rich.console import Console
from termcoder.plugins.base import BasePlugin

class {name.title().replace("_", "").replace("-", "")}Plugin(BasePlugin):
    name = "{name.lower()}"
    description = "Custom plugin description"
    version = "0.1.0"

    def register_commands(self) -> Dict[str, Callable[[List[str]], None]]:
        return {{
            "{name.lower()}": self.run_command,
        }}

    def register_tools(self, registry) -> None:
        registry.register_custom_tool(
            name="{name.lower()}_tool",
            description="Custom tool description",
            parameters={{"type": "object", "properties": {{"arg": {{"type": "string"}}}}}},
            handler=self.run_tool,
        )

    def run_command(self, args: List[str]) -> None:
        console = Console()
        console.print(f"[bold green]Plugin {name} executed with args:[/bold green] {{args}}")

    def run_tool(self, arg: str = "") -> str:
        return f"Tool executed with argument: {{arg}}"
'''
        file_path.write_text(template, encoding="utf-8")
        return file_path
