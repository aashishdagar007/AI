"""Built-in system information plugin for TermCoder."""

from __future__ import annotations

import platform
import shutil
import sys
from typing import Any, Callable, Dict, List, TYPE_CHECKING
from rich.console import Console
from rich.panel import Panel

from termcoder.plugins.base import BasePlugin

if TYPE_CHECKING:
    from termcoder.agent.tools import ToolRegistry


class SystemInfoPlugin(BasePlugin):
    name = "system_info"
    description = "Displays host OS, Python, and disk specifications"
    version = "1.0.0"

    def register_commands(self) -> Dict[str, Callable[[List[str]], None]]:
        return {"sysinfo": self._cmd_sysinfo}

    def register_tools(self, registry: "ToolRegistry") -> None:
        registry.register_custom_tool(
            name="get_system_specs",
            description="Get host operating system, Python version, and free disk space.",
            parameters={"type": "object", "properties": {}},
            handler=self._tool_get_specs,
        )

    def _get_info_dict(self) -> Dict[str, Any]:
        total, used, free = shutil.disk_usage(".")
        return {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
            "disk_free_gb": round(free / (1024 ** 3), 2),
            "disk_total_gb": round(total / (1024 ** 3), 2),
        }

    def _cmd_sysinfo(self, args: List[str]) -> None:
        info = self._get_info_dict()
        console = Console()
        text = (
            f"[bold cyan]OS:[/bold cyan] {info['os']} {info['os_release']} ({info['machine']})\n"
            f"[bold cyan]Python:[/bold cyan] {info['python']}\n"
            f"[bold cyan]Disk:[/bold cyan] {info['disk_free_gb']} GB free of {info['disk_total_gb']} GB"
        )
        console.print(Panel(text, title="System Diagnostics", border_style="cyan"))

    def _tool_get_specs(self) -> str:
        info = self._get_info_dict()
        return (
            f"OS: {info['os']} {info['os_release']} ({info['machine']}), "
            f"Python: {info['python']}, "
            f"Disk Free: {info['disk_free_gb']} GB / {info['disk_total_gb']} GB"
        )
