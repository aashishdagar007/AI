"""Tests for plugin architecture and lifecycle."""

import tempfile
from pathlib import Path
import pytest

from termcoder.agent.tools import ToolRegistry
from termcoder.plugins.base import BasePlugin
from termcoder.plugins.manager import PluginManager


class SamplePlugin(BasePlugin):
    name = "sample_test"
    description = "A sample test plugin"
    version = "1.0.0"

    def register_commands(self):
        return {"custom_cmd": lambda args: "executed"}

    def register_tools(self, registry):
        registry.register_custom_tool(
            name="plugin_tool",
            description="Tool from plugin",
            parameters={"type": "object", "properties": {}},
            handler=lambda: "plugin tool success",
        )


def test_plugin_registration():
    registry = ToolRegistry(workspace_root=".", auto_approve=True)
    manager = PluginManager(workspace_root=".")

    sample = SamplePlugin()
    manager._register_plugin_instance(sample, registry)

    assert "sample_test" in manager.plugins
    assert manager.get_command("custom_cmd") is not None

    tool_res = registry.execute_tool("plugin_tool", {})
    assert tool_res == "plugin tool success"


def test_plugin_scaffolding():
    with tempfile.TemporaryDirectory() as tmpdir:
        scaffold_path = PluginManager.create_plugin_scaffold("weather_checker", target_dir=Path(tmpdir))
        assert scaffold_path.exists()
        content = scaffold_path.read_text(encoding="utf-8")
        assert "class WeatherCheckerPlugin" in content
        assert 'name = "weather_checker"' in content
