"""Dynamic model fetching, parsing, and management for NVIDIA NIM and OpenAI-compatible APIs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx


@dataclass
class ModelInfo:
    id: str
    name: str
    owner: str = ""
    context_length: Optional[int] = None
    description: str = ""
    is_recommended: bool = False


# Well-known top coding & reasoning models currently active on NVIDIA NIM
RECOMMENDED_MODELS = [
    "mistralai/mistral-large-2-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "mistralai/codestral-22b-instruct-v0.1",
    "deepseek-ai/deepseek-v4-pro-0813",
    "deepseek-ai/deepseek-coder-6.7b-instruct",
    "google/gemma-3-12b-it",
    "microsoft/phi-3.5-moe-instruct",
]


class ModelManager:
    """Handles querying and selecting models dynamically from NVIDIA NIM."""

    def __init__(self, base_url: str = "https://integrate.api.nvidia.com/v1", api_key: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._cached_models: List[ModelInfo] = []

    def update_credentials(self, api_key: str, base_url: Optional[str] = None) -> None:
        """Update active API key and refresh model cache."""
        self.api_key = api_key
        if base_url:
            self.base_url = base_url.rstrip("/")
        self._cached_models = []

    def validate_api_key(self, api_key: Optional[str] = None) -> tuple[bool, str]:
        """Test whether the provided API key is valid against NVIDIA NIM."""
        key = api_key or self.api_key
        if not key:
            return False, "No API key provided."

        url = f"{self.base_url}/models"
        headers = {
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "User-Agent": "TermCoder/0.1.0",
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers=headers)
                if res.status_code == 200:
                    return True, "API Key is valid and active on NVIDIA NIM."
                elif res.status_code == 401:
                    return False, "Authentication failed: Invalid API key (HTTP 401)."
                elif res.status_code == 403:
                    return False, "Access forbidden: API key lacks permission (HTTP 403)."
                else:
                    return False, f"Server responded with status {res.status_code}: {res.text[:150]}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def fetch_models(self, query: str = "", force_refresh: bool = False) -> List[ModelInfo]:
        """Fetch models dynamically from the provider API endpoint."""
        if self._cached_models and not force_refresh:
            models = self._cached_models
        else:
            models = self._fetch_from_api()
            self._cached_models = models

        if query:
            q = query.lower()
            return [m for m in models if q in m.id.lower() or q in m.name.lower() or q in m.owner.lower()]
        return models

    def _fetch_from_api(self) -> List[ModelInfo]:
        """Query the /models endpoint with the current API key."""
        if not self.api_key:
            # Fallback to recommended list if no API key is configured yet
            return [
                ModelInfo(
                    id=m_id,
                    name=m_id.split("/")[-1] if "/" in m_id else m_id,
                    owner=m_id.split("/")[0] if "/" in m_id else "nvidia",
                    is_recommended=True,
                    description="High performance free model on NVIDIA NIM",
                )
                for m_id in RECOMMENDED_MODELS
            ]

        url = f"{self.base_url}/models"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "User-Agent": "TermCoder/0.1.0",
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code != 200:
                    # Return recommended models with error note
                    return [
                        ModelInfo(
                            id=m_id,
                            name=m_id.split("/")[-1] if "/" in m_id else m_id,
                            owner=m_id.split("/")[0] if "/" in m_id else "nvidia",
                            is_recommended=True,
                            description=f"Fallback list (API returned {resp.status_code})",
                        )
                        for m_id in RECOMMENDED_MODELS
                    ]

                data = resp.json()
                raw_list = data.get("data", []) if isinstance(data, dict) else data
                results: List[ModelInfo] = []

                for item in raw_list:
                    if isinstance(item, dict):
                        m_id = item.get("id", "")
                        if not m_id:
                            continue
                        owner = item.get("owned_by", "") or (m_id.split("/")[0] if "/" in m_id else "")
                        is_rec = m_id in RECOMMENDED_MODELS or any(rec in m_id for rec in ["llama-3.3", "deepseek-r1", "nemotron"])
                        results.append(
                            ModelInfo(
                                id=m_id,
                                name=m_id.split("/")[-1] if "/" in m_id else m_id,
                                owner=owner,
                                is_recommended=is_rec,
                            )
                        )

                # Sort: recommended first, then alphabetically
                results.sort(key=lambda m: (not m.is_recommended, m.id))
                return results if results else [
                    ModelInfo(id=m_id, name=m_id, is_recommended=True) for m_id in RECOMMENDED_MODELS
                ]

        except Exception as e:
            return [
                ModelInfo(
                    id=m_id,
                    name=m_id.split("/")[-1] if "/" in m_id else m_id,
                    owner=m_id.split("/")[0] if "/" in m_id else "nvidia",
                    is_recommended=True,
                    description=f"Offline fallback list: {str(e)[:40]}",
                )
                for m_id in RECOMMENDED_MODELS
            ]
