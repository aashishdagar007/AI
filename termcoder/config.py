"""Configuration management for TermCoder."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CONFIG_DIR = Path.home() / ".termcoder"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_HISTORY_FILE = DEFAULT_CONFIG_DIR / "history.txt"
DEFAULT_PLUGINS_DIR = DEFAULT_CONFIG_DIR / "plugins"

# Default to NVIDIA NIM with free/available powerful model
DEFAULT_PROVIDER = "nvidia"
DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "mistralai/mistral-large-2-instruct"


@dataclass
class Config:
    api_key: str = ""
    provider: str = DEFAULT_PROVIDER
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    auto_approve: bool = False
    stream_output: bool = True
    system_prompt_extra: str = ""
    max_context_tokens: int = 128000
    theme: str = "default"
    _config_path: Optional[Path] = None

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """Load configuration from disk with environment variable fallbacks."""
        path = config_path or DEFAULT_CONFIG_FILE
        cfg = cls(_config_path=path)

        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, val in data.items():
                        if hasattr(cfg, key) and not key.startswith("_"):
                            setattr(cfg, key, val)
            except Exception as e:
                # Corrupted or unreadable config, proceed with defaults
                pass

        # Environment variable fallback if not set in config file
        env_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("TERMCODER_API_KEY")
        if env_key and not cfg.api_key:
            cfg.api_key = env_key

        env_model = os.environ.get("TERMCODER_MODEL")
        if env_model:
            cfg.model = env_model

        env_base_url = os.environ.get("TERMCODER_BASE_URL")
        if env_base_url:
            cfg.base_url = env_base_url

        return cfg

    def save(self, config_path: Optional[Path] = None) -> None:
        """Persist current configuration to disk."""
        path = config_path or self._config_path or DEFAULT_CONFIG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v for k, v in asdict(self).items() if not k.startswith("_")}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def set_api_key(self, new_key: str, persist: bool = True) -> None:
        """Modify the active API key and optionally save to disk."""
        self.api_key = new_key.strip()
        if persist:
            self.save()

    def set_model(self, new_model: str, persist: bool = True) -> None:
        """Modify the active model and optionally save to disk."""
        self.model = new_model.strip()
        if persist:
            self.save()

    def masked_api_key(self) -> str:
        """Return a securely masked representation of the active API key."""
        if not self.api_key:
            return "(not configured)"
        key = self.api_key.strip()
        if len(key) <= 10:
            return key[:2] + "****" + key[-2:]
        return f"{key[:6]}...{key[-4:]}"


# Global singleton instance
_GLOBAL_CONFIG: Optional[Config] = None


def get_config() -> Config:
    """Get or load the global config singleton."""
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = Config.load()
    return _GLOBAL_CONFIG


def reload_config() -> Config:
    """Reload config from disk/env."""
    global _GLOBAL_CONFIG
    _GLOBAL_CONFIG = Config.load()
    return _GLOBAL_CONFIG
