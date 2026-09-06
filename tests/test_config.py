"""Tests for TermCoder configuration and runtime key modification."""

import json
from pathlib import Path
import tempfile
import pytest

from termcoder.config import Config


def test_config_defaults():
    cfg = Config()
    assert cfg.provider == "nvidia"
    assert "nvidia.com" in cfg.base_url
    assert cfg.masked_api_key() == "(not configured)"


def test_config_set_api_key_and_masking():
    with tempfile.TemporaryDirectory() as tmpdir:
        conf_file = Path(tmpdir) / "config.json"
        cfg = Config.load(config_path=conf_file)

        # Set new key
        cfg.set_api_key("nvapi-1234567890abcdef", persist=True)
        assert cfg.api_key == "nvapi-1234567890abcdef"
        assert cfg.masked_api_key().startswith("nvapi-")
        assert "..." in cfg.masked_api_key()

        # Reload from disk and verify persistence
        reloaded = Config.load(config_path=conf_file)
        assert reloaded.api_key == "nvapi-1234567890abcdef"


def test_config_runtime_modification():
    cfg = Config()
    cfg.set_api_key("key_alpha", persist=False)
    assert cfg.api_key == "key_alpha"

    # Modify again at runtime
    cfg.set_api_key("key_beta", persist=False)
    assert cfg.api_key == "key_beta"


def test_config_set_model():
    cfg = Config()
    cfg.set_model("deepseek-ai/deepseek-r1", persist=False)
    assert cfg.model == "deepseek-ai/deepseek-r1"
