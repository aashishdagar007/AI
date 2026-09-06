"""Tests for agent tools execution, file editing, and registry."""

import tempfile
from pathlib import Path
import pytest

from termcoder.agent.tools import ToolRegistry


def test_tool_file_operations():
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry(workspace_root=tmpdir, auto_approve=True)

        # 1. Write file
        res_write = registry.execute_tool("write_file", {"path": "test.txt", "content": "Hello World\nLine 2\nLine 3"})
        assert "Successfully wrote" in res_write

        # 2. Read file
        res_read = registry.execute_tool("read_file", {"path": "test.txt", "start_line": 1, "end_line": 2})
        assert "Hello World" in res_read
        assert "Line 2" in res_read
        assert "Line 3" not in res_read

        # 3. Edit file
        res_edit = registry.execute_tool(
            "edit_file",
            {"path": "test.txt", "search_content": "Line 2", "replace_content": "Replaced Line 2"},
        )
        assert "Successfully edited" in res_edit

        # 4. Verify edit
        res_verify = registry.execute_tool("read_file", {"path": "test.txt"})
        assert "Replaced Line 2" in res_verify

        # 5. List directory
        res_list = registry.execute_tool("list_directory", {"path": "."})
        assert "test.txt" in res_list


def test_tool_command_approval_rejection():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Deny callback
        registry = ToolRegistry(
            workspace_root=tmpdir,
            auto_approve=False,
            confirm_callback=lambda cmd: False,
        )

        res = registry.execute_tool("run_terminal_command", {"command": "echo 'forbidden'"})
        assert "Command execution cancelled by user" in res


def test_tool_command_approval_acceptance():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Approve callback
        registry = ToolRegistry(
            workspace_root=tmpdir,
            auto_approve=False,
            confirm_callback=lambda cmd: True,
        )

        res = registry.execute_tool("run_terminal_command", {"command": "python -c \"print('approved_output')\""})
        assert "approved_output" in res
        assert "Exit code: 0" in res


def test_custom_tool_registration():
    registry = ToolRegistry(workspace_root=".", auto_approve=True)

    def my_calc(a: int, b: int) -> int:
        return a * b

    registry.register_custom_tool(
        name="multiply",
        description="Multiply two numbers",
        parameters={"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}},
        handler=my_calc,
    )

    schemas = registry.get_tool_schemas()
    assert any(s["function"]["name"] == "multiply" for s in schemas)

    res = registry.execute_tool("multiply", {"a": 6, "b": 7})
    assert res == "42"
