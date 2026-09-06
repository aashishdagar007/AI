"""Tool definitions, execution handlers, and registry for TermCoder agent."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from termcoder.context.indexer import CodebaseIndexer
from termcoder.context.retriever import ContextRetriever


class ToolRegistry:
    """Registry managing available LLM tools and their handlers."""

    def __init__(
        self,
        workspace_root: Path | str = ".",
        auto_approve: bool = False,
        confirm_callback: Optional[Callable[[str], bool]] = None,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.auto_approve = auto_approve
        self.confirm_callback = confirm_callback
        self.indexer = CodebaseIndexer(self.workspace_root)
        self.retriever = ContextRetriever(self.indexer)
        self.custom_tools: Dict[str, Dict[str, Any]] = {}

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return full list of tool schemas for LLM chat completion API."""
        builtins = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read contents of a file in the workspace, optionally specifying line numbers (1-indexed).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative or absolute path to the file"},
                            "start_line": {"type": "integer", "description": "Starting line number (1-indexed, optional)"},
                            "end_line": {"type": "integer", "description": "Ending line number (inclusive, optional)"},
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Create or overwrite a file with given text content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative or absolute path to the file"},
                            "content": {"type": "string", "description": "Full file content to write"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Replace a specific substring or code block inside an existing file with new content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file to edit"},
                            "search_content": {"type": "string", "description": "Exact text block to find and replace"},
                            "replace_content": {"type": "string", "description": "New replacement text"},
                        },
                        "required": ["path", "search_content", "replace_content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "List files and directories within a given path.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Directory path (default: current directory '.')"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_code",
                    "description": "Search for a keyword or regex pattern across workspace code files.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Text or regex pattern to search for"},
                            "is_regex": {"type": "boolean", "description": "Whether query is a regular expression (default: false)"},
                            "path": {"type": "string", "description": "Optional subfolder or path filter"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_terminal_command",
                    "description": "Execute a shell command (PowerShell / CMD) on the user's machine (e.g. run tests, build, git).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Command line to run"},
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "git_status",
                    "description": "Get current git working tree status (untracked, modified, and staged files).",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "git_diff",
                    "description": "Show git diff of unstaged or staged changes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "staged": {"type": "boolean", "description": "If true, view diff of staged changes; else unstaged (default: false)"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "git_commit",
                    "description": "Stage files and create a git commit with a descriptive message.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "Commit message"},
                            "stage_all": {"type": "boolean", "description": "Whether to stage all tracked/untracked changes with `git add -A` (default: true)"},
                        },
                        "required": ["message"],
                    },
                },
            },
        ]

        # Add custom tools registered by plugins
        for tool_name, info in self.custom_tools.items():
            builtins.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": info.get("description", ""),
                    "parameters": info.get("parameters", {"type": "object", "properties": {}}),
                },
            })

        return builtins

    def register_custom_tool(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable[..., Any],
    ) -> None:
        """Register a custom tool from a plugin."""
        self.custom_tools[name] = {
            "description": description,
            "parameters": parameters,
            "handler": handler,
        }

    def execute_tool(self, name: str, args: dict) -> str:
        """Execute a tool by name and return string result."""
        try:
            if name == "read_file":
                return self._read_file(
                    path=args.get("path", ""),
                    start_line=args.get("start_line"),
                    end_line=args.get("end_line"),
                )
            elif name == "write_file":
                return self._write_file(
                    path=args.get("path", ""),
                    content=args.get("content", ""),
                )
            elif name == "edit_file":
                return self._edit_file(
                    path=args.get("path", ""),
                    search_content=args.get("search_content", ""),
                    replace_content=args.get("replace_content", ""),
                )
            elif name == "list_directory":
                return self._list_directory(path=args.get("path", "."))
            elif name == "search_code":
                return self._search_code(
                    query=args.get("query", ""),
                    is_regex=args.get("is_regex", False),
                    path_filter=args.get("path", ""),
                )
            elif name == "run_terminal_command":
                return self._run_terminal_command(command=args.get("command", ""))
            elif name == "git_status":
                return self._git_status()
            elif name == "git_diff":
                return self._git_diff(staged=args.get("staged", False))
            elif name == "git_commit":
                return self._git_commit(
                    message=args.get("message", ""),
                    stage_all=args.get("stage_all", True),
                )
            elif name in self.custom_tools:
                handler = self.custom_tools[name]["handler"]
                res = handler(**args)
                return str(res)
            else:
                return f"Error: Unknown tool '{name}'."
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

    def _resolve_path(self, path_str: str) -> Path:
        """Safely resolve path within workspace."""
        p = Path(path_str)
        if not p.is_absolute():
            p = (self.workspace_root / p).resolve()
        return p

    def _read_file(self, path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
        target = self._resolve_path(path)
        if not target.exists():
            return f"Error: File '{path}' does not exist."
        if not target.is_file():
            return f"Error: '{path}' is not a file."

        try:
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
            total_lines = len(lines)

            s = max(1, start_line or 1)
            e = min(total_lines, end_line or total_lines)

            if s > total_lines:
                return f"File '{path}' has only {total_lines} lines. (Requested start: {s})"

            selected = lines[s - 1 : e]
            numbered = [f"{idx:4d} | {line}" for idx, line in enumerate(selected, start=s)]
            header = f"=== File: {path} (Lines {s}-{e} of {total_lines}) ===\n"
            return header + "\n".join(numbered)
        except Exception as e:
            return f"Error reading file '{path}': {e}"

    def _write_file(self, path: str, content: str) -> str:
        target = self._resolve_path(path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"Successfully wrote {len(content)} characters to '{path}'."
        except Exception as e:
            return f"Error writing to '{path}': {e}"

    def _edit_file(self, path: str, search_content: str, replace_content: str) -> str:
        target = self._resolve_path(path)
        if not target.exists():
            return f"Error: File '{path}' does not exist."

        try:
            current = target.read_text(encoding="utf-8")
            if search_content not in current:
                # Try normalized newlines match
                norm_current = current.replace("\r\n", "\n")
                norm_search = search_content.replace("\r\n", "\n")
                norm_replace = replace_content.replace("\r\n", "\n")
                if norm_search in norm_current:
                    updated = norm_current.replace(norm_search, norm_replace, 1)
                    target.write_text(updated, encoding="utf-8")
                    return f"Successfully edited '{path}' (normalized newlines)."
                return f"Error: Could not find target code snippet in '{path}'. Make sure it matches exactly."

            updated = current.replace(search_content, replace_content, 1)
            target.write_text(updated, encoding="utf-8")
            return f"Successfully edited '{path}'."
        except Exception as e:
            return f"Error editing '{path}': {e}"

    def _list_directory(self, path: str = ".") -> str:
        target = self._resolve_path(path)
        if not target.exists():
            return f"Error: Path '{path}' does not exist."
        if not target.is_dir():
            return f"Error: '{path}' is not a directory."

        try:
            items = sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            output = [f"Contents of '{path}':"]
            for item in items:
                prefix = "[DIR] " if item.is_dir() else "      "
                output.append(f"  {prefix} {item.name}")
            return "\n".join(output)
        except Exception as e:
            return f"Error listing directory '{path}': {e}"

    def _search_code(self, query: str, is_regex: bool = False, path_filter: str = "") -> str:
        results = self.retriever.search_code(query=query, is_regex=is_regex, path_filter=path_filter)
        if not results:
            return f"No matches found for '{query}'."

        lines = [f"Found {len(results)} matches for '{query}':"]
        for match in results:
            lines.append(f"{match['file']}:{match['line']}: {match['content']}")
        return "\n".join(lines)

    def _run_terminal_command(self, command: str) -> str:
        # Prompt user if confirmation callback provided and not auto-approved
        if not self.auto_approve and self.confirm_callback:
            allowed = self.confirm_callback(command)
            if not allowed:
                return f"Command execution cancelled by user: '{command}'"

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=120,
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            code = result.returncode

            output_lines = [f"Exit code: {code}"]
            if stdout:
                output_lines.append(f"STDOUT:\n{stdout}")
            if stderr:
                output_lines.append(f"STDERR:\n{stderr}")
            if not stdout and not stderr:
                output_lines.append("(No output produced)")

            return "\n".join(output_lines)
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after 120 seconds: '{command}'"
        except Exception as e:
            return f"Error running command '{command}': {e}"

    def _git_status(self) -> str:
        res = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(self.workspace_root),
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            return f"Git error: {res.stderr.strip()}"
        out = res.stdout.strip()
        return f"Git status:\n{out}" if out else "Git status: Working tree clean, nothing to commit."

    def _git_diff(self, staged: bool = False) -> str:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")
        res = subprocess.run(
            cmd,
            cwd=str(self.workspace_root),
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            return f"Git error: {res.stderr.strip()}"
        out = res.stdout.strip()
        label = "staged" if staged else "unstaged"
        return f"Git diff ({label}):\n{out}" if out else f"No {label} changes."

    def _git_commit(self, message: str, stage_all: bool = True) -> str:
        if stage_all:
            stage_res = subprocess.run(
                ["git", "add", "-A"],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
            )
            if stage_res.returncode != 0:
                return f"Git add error: {stage_res.stderr.strip()}"

        commit_res = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(self.workspace_root),
            capture_output=True,
            text=True,
        )
        if commit_res.returncode != 0:
            return f"Git commit failed: {commit_res.stderr.strip() or commit_res.stdout.strip()}"
        return f"Git commit succeeded:\n{commit_res.stdout.strip()}"
