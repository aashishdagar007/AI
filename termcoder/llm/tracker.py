"""Token tracking and usage metrics for TermCoder."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class TurnUsage:
    """Usage metrics for a single request/turn."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    model: str = ""

    @classmethod
    def from_api_dict(cls, usage_dict: dict, model: str = "") -> "TurnUsage":
        prompt = usage_dict.get("prompt_tokens", 0)
        completion = usage_dict.get("completion_tokens", 0)
        total = usage_dict.get("total_tokens", prompt + completion)
        
        # Check for cached prompt tokens if returned by provider
        cached = 0
        prompt_details = usage_dict.get("prompt_tokens_details") or {}
        if isinstance(prompt_details, dict):
            cached = prompt_details.get("cached_tokens", 0)

        return cls(
            prompt_tokens=prompt,
            completion_tokens=completion,
            cached_tokens=cached,
            total_tokens=total,
            model=model,
        )


class TokenTracker:
    """Maintains token metrics across the entire interactive session."""

    def __init__(self) -> None:
        self.history: List[TurnUsage] = []
        self.session_prompt_tokens: int = 0
        self.session_completion_tokens: int = 0
        self.session_total_tokens: int = 0
        self.session_turns: int = 0

    def record_usage(self, usage: TurnUsage) -> None:
        """Record token usage from a completed LLM turn."""
        self.history.append(usage)
        self.session_prompt_tokens += usage.prompt_tokens
        self.session_completion_tokens += usage.completion_tokens
        self.session_total_tokens += usage.total_tokens
        self.session_turns += 1

    def latest_turn(self) -> TurnUsage:
        """Get token usage of the most recent turn."""
        if self.history:
            return self.history[-1]
        return TurnUsage()

    def format_summary_line(self) -> str:
        """Format a concise inline status line showing turn and session tokens."""
        latest = self.latest_turn()
        if self.session_turns == 0:
            return "Tokens: 0 (session start)"
        
        cached_str = f" ({latest.cached_tokens} cached)" if latest.cached_tokens > 0 else ""
        return (
            f"Tokens: {latest.prompt_tokens:,} in{cached_str} + {latest.completion_tokens:,} out "
            f"= {latest.total_tokens:,} turn | Session Total: {self.session_total_tokens:,}"
        )

    def reset(self) -> None:
        """Reset session statistics."""
        self.history.clear()
        self.session_prompt_tokens = 0
        self.session_completion_tokens = 0
        self.session_total_tokens = 0
        self.session_turns = 0
