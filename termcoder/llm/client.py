"""NVIDIA NIM and OpenAI-compatible LLM streaming client with tool calling and token accounting."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional
import httpx

from termcoder.llm.tracker import TokenTracker, TurnUsage


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
    raw_arguments: str = ""


@dataclass
class LLMResponse:
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: Optional[TurnUsage] = None
    finish_reason: str = ""


class LLMClient:
    """Client for NVIDIA NIM / OpenAI-compatible API."""

    def __init__(
        self,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        api_key: str = "",
        model: str = "meta/llama-3.3-70b-instruct",
        tracker: Optional[TokenTracker] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.tracker = tracker or TokenTracker()

    def update_credentials(self, api_key: str, base_url: Optional[str] = None) -> None:
        """Dynamically switch API key and/or base URL at runtime."""
        self.api_key = api_key
        if base_url:
            self.base_url = base_url.rstrip("/")

    def set_model(self, model: str) -> None:
        """Dynamically switch active model."""
        self.model = model

    def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> LLMResponse:
        """
        Send a chat completion request with streaming.
        Invokes on_chunk callback as text arrives, and returns the final LLMResponse.
        """
        if not self.api_key:
            raise ValueError(
                "NVIDIA NIM API key is not configured. Please use `/key <your_key>` or set NVIDIA_API_KEY."
            )

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": "TermCoder/0.1.0",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        content_accumulator: List[str] = []
        tool_call_map: Dict[int, Dict[str, Any]] = {}
        finish_reason = ""
        usage_data: Optional[dict] = None

        with httpx.Client(timeout=60.0) as client:
            try:
                with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        err_text = response.read().decode("utf-8", errors="replace")
                        if response.status_code in (401, 403):
                            raise RuntimeError(
                                f"NVIDIA NIM Authentication failed (HTTP {response.status_code}): {err_text}\n"
                                "Your API key may have expired or exhausted its free credits.\n"
                                "Please update your key in this session using `/key <your_new_key>` or generate one at https://build.nvidia.com"
                            )
                        elif response.status_code == 410:
                            raise RuntimeError(
                                f"NVIDIA NIM Model Error (HTTP 410): {err_text}\n"
                                f"The active model '{self.model}' is no longer available. Use `/models` to browse active models and `/model <model_id>` to switch."
                            )
                        raise RuntimeError(
                            f"NVIDIA NIM API Error (HTTP {response.status_code}): {err_text}"
                        )

                    for line in response.iter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            raw_data = line[6:].strip()
                            if raw_data == "[DONE]":
                                break

                            try:
                                chunk = json.loads(raw_data)
                            except json.JSONDecodeError:
                                continue

                            # Extract usage if present in chunk
                            if "usage" in chunk and chunk["usage"]:
                                usage_data = chunk["usage"]

                            choices = chunk.get("choices", [])
                            if not choices:
                                continue

                            choice = choices[0]
                            delta = choice.get("delta", {})

                            # Content chunk
                            if "content" in delta and delta["content"]:
                                text_chunk = delta["content"]
                                content_accumulator.append(text_chunk)
                                if on_chunk:
                                    on_chunk(text_chunk)

                            # Finish reason
                            if choice.get("finish_reason"):
                                finish_reason = choice["finish_reason"]

                            # Tool calls chunk
                            if "tool_calls" in delta and delta["tool_calls"]:
                                for tc in delta["tool_calls"]:
                                    idx = tc.get("index", 0)
                                    if idx not in tool_call_map:
                                        tool_call_map[idx] = {
                                            "id": tc.get("id", f"call_{idx}"),
                                            "name": tc.get("function", {}).get("name", ""),
                                            "arguments": "",
                                        }
                                    fn = tc.get("function", {})
                                    if "name" in fn and fn["name"]:
                                        tool_call_map[idx]["name"] = fn["name"]
                                    if "arguments" in fn and fn["arguments"]:
                                        tool_call_map[idx]["arguments"] += fn["arguments"]

            except httpx.RequestError as exc:
                raise RuntimeError(f"Network error connecting to NVIDIA NIM ({self.base_url}): {exc}")

        # Assemble full content
        full_content = "".join(content_accumulator)

        # Parse assembled tool calls
        assembled_tool_calls: List[ToolCall] = []
        for idx in sorted(tool_call_map.keys()):
            tc_data = tool_call_map[idx]
            arg_str = tc_data["arguments"]
            parsed_args = {}
            if arg_str.strip():
                try:
                    parsed_args = json.loads(arg_str)
                except json.JSONDecodeError:
                    parsed_args = {"raw": arg_str}
            assembled_tool_calls.append(
                ToolCall(
                    id=tc_data["id"],
                    name=tc_data["name"],
                    arguments=parsed_args,
                    raw_arguments=arg_str,
                )
            )

        # Fallback parsing: if model emitted JSON tool call block in text
        if not assembled_tool_calls and "<tool_call>" in full_content:
            assembled_tool_calls = self._parse_text_tool_calls(full_content)

        # Calculate token usage
        turn_usage: Optional[TurnUsage] = None
        if usage_data:
            turn_usage = TurnUsage.from_api_dict(usage_data, model=self.model)
        else:
            # Approximate estimate if usage was omitted by stream
            prompt_est = sum(len(str(m.get("content", ""))) for m in messages) // 4
            comp_est = len(full_content) // 4
            turn_usage = TurnUsage(
                prompt_tokens=prompt_est,
                completion_tokens=comp_est,
                total_tokens=prompt_est + comp_est,
                model=self.model,
            )

        self.tracker.record_usage(turn_usage)

        return LLMResponse(
            content=full_content,
            tool_calls=assembled_tool_calls,
            usage=turn_usage,
            finish_reason=finish_reason,
        )

    def _parse_text_tool_calls(self, text: str) -> List[ToolCall]:
        """Extract tool calls embedded in <tool_call> JSON tags if returned by model."""
        import re
        calls = []
        pattern = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
        for i, match in enumerate(pattern.finditer(text)):
            try:
                data = json.loads(match.group(1))
                calls.append(
                    ToolCall(
                        id=f"text_call_{i}",
                        name=data.get("name", ""),
                        arguments=data.get("arguments", {}),
                        raw_arguments=match.group(1),
                    )
                )
            except Exception:
                continue
        return calls
