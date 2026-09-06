"""Tests for token tracker, model manager, and LLM structures."""

from unittest.mock import MagicMock, patch
import pytest

from termcoder.llm.models import ModelManager, RECOMMENDED_MODELS
from termcoder.llm.tracker import TokenTracker, TurnUsage


def test_token_tracker_recording():
    tracker = TokenTracker()
    assert tracker.session_total_tokens == 0

    # Record first turn
    turn1 = TurnUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150, model="meta/llama-3.3-70b-instruct")
    tracker.record_usage(turn1)

    assert tracker.session_turns == 1
    assert tracker.session_prompt_tokens == 100
    assert tracker.session_completion_tokens == 50
    assert tracker.session_total_tokens == 150

    # Record second turn
    turn2 = TurnUsage(prompt_tokens=200, completion_tokens=80, total_tokens=280, model="meta/llama-3.3-70b-instruct")
    tracker.record_usage(turn2)

    assert tracker.session_turns == 2
    assert tracker.session_total_tokens == 430
    assert tracker.latest_turn().total_tokens == 280

    summary = tracker.format_summary_line()
    assert "200 in + 80 out = 280 turn" in summary
    assert "Session Total: 430" in summary


def test_token_tracker_reset():
    tracker = TokenTracker()
    tracker.record_usage(TurnUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20))
    assert tracker.session_turns == 1

    tracker.reset()
    assert tracker.session_turns == 0
    assert tracker.session_total_tokens == 0


def test_model_manager_fallback_recommended():
    # Without an API key, should return recommended NVIDIA NIM models
    manager = ModelManager(api_key="")
    models = manager.fetch_models()
    assert len(models) >= len(RECOMMENDED_MODELS)
    assert any(m.id == "mistralai/mistral-large-2-instruct" for m in models)


def test_model_manager_query_filter():
    manager = ModelManager(api_key="")
    llama_models = manager.fetch_models(query="llama")
    assert all("llama" in m.id.lower() for m in llama_models)
    assert len(llama_models) > 0


def test_model_manager_credential_update():
    manager = ModelManager(api_key="old_key")
    manager.update_credentials("new_key_nvapi")
    assert manager.api_key == "new_key_nvapi"


def test_llm_client_runtime_key_update():
    from termcoder.llm.client import LLMClient
    client = LLMClient(api_key="old_nvapi_key")
    assert client.api_key == "old_nvapi_key"

    # User modifies key anytime
    client.update_credentials("new_nvapi_key_456")
    assert client.api_key == "new_nvapi_key_456"

    # User changes model anytime
    client.set_model("deepseek-ai/deepseek-v4-pro-0813")
    assert client.model == "deepseek-ai/deepseek-v4-pro-0813"
