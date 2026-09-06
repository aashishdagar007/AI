"""Autonomous ReAct agent loop for TermCoder."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional
from termcoder.agent.prompts import SYSTEM_PROMPT
from termcoder.agent.tools import ToolRegistry
from termcoder.context.indexer import CodebaseIndexer
from termcoder.context.repo_map import RepoMapGenerator
from termcoder.context.retriever import ContextRetriever
from termcoder.llm.client import LLMClient, LLMResponse, ToolCall
from termcoder.llm.tracker import TokenTracker


class AgentLoop:
    """Orchestrates LLM turns and tool executions."""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        max_iterations: int = 15,
        on_chunk: Optional[Callable[[str], None]] = None,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
        on_tool_result: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.client = llm_client
        self.tools = tool_registry
        self.max_iterations = max_iterations
        self.on_chunk = on_chunk
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result

        # Context engines
        self.indexer = self.tools.indexer
        self.repo_map_gen = RepoMapGenerator(self.indexer)
        self.retriever = self.tools.retriever

        # Conversation history
        self.messages: List[Dict[str, Any]] = []
        self._init_system_prompt()

    def _init_system_prompt(self) -> None:
        """Initialize base system prompt with repository map."""
        repo_map = self.repo_map_gen.generate_map(max_tokens_approx=2500)
        full_system = f"{SYSTEM_PROMPT}\n\n### Current Project Structure\n{repo_map}"
        self.messages = [{"role": "system", "content": full_system}]

    def refresh_context(self) -> None:
        """Refresh repository map in system prompt after file changes."""
        self._init_system_prompt()

    def clear_history(self) -> None:
        """Reset conversation messages back to system prompt."""
        self._init_system_prompt()

    def run_turn(self, user_prompt: str) -> str:
        """
        Execute one user request through the ReAct agent loop.
        Returns final text response.
        """
        # Resolve any @file or @dir mentions
        cleaned_prompt, attached_files = self.retriever.resolve_mentions(user_prompt)

        user_content_parts = []
        if attached_files:
            user_content_parts.append("### Attached File Contexts:")
            for att in attached_files:
                user_content_parts.append(
                    f"--- File: {att['path']} ---\n{att['content']}\n--- End File ---"
                )
            user_content_parts.append("\nUser Request:")

        user_content_parts.append(cleaned_prompt)
        final_user_content = "\n".join(user_content_parts)

        self.messages.append({"role": "user", "content": final_user_content})

        schemas = self.tools.get_tool_schemas()
        iterations = 0

        while iterations < self.max_iterations:
            iterations += 1

            # Call LLM with streaming and tools
            resp = self.client.stream_chat(
                messages=self.messages,
                tools=schemas,
                on_chunk=self.on_chunk,
            )

            # Record assistant turn
            assistant_msg: Dict[str, Any] = {"role": "assistant"}
            if resp.content:
                assistant_msg["content"] = resp.content

            if resp.tool_calls:
                # Format tool calls in OpenAI message format
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.raw_arguments if tc.raw_arguments else json.dumps(tc.arguments),
                        },
                    }
                    for tc in resp.tool_calls
                ]
                self.messages.append(assistant_msg)

                # Execute requested tools
                for tc in resp.tool_calls:
                    if self.on_tool_call:
                        self.on_tool_call(tc.name, tc.arguments)

                    tool_output = self.tools.execute_tool(tc.name, tc.arguments)

                    if self.on_tool_result:
                        self.on_tool_result(tc.name, tool_output)

                    # Append tool result to conversation history
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.name,
                        "content": str(tool_output),
                    })

                # Re-run LLM with tool outputs
                continue
            else:
                # No tool calls; final response completed
                if resp.content:
                    self.messages.append(assistant_msg)
                return resp.content

        return "TermCoder reached the maximum tool iteration limit for this request."
