"""Fail-proof Google Gemini client with dynamic multi-model failover and rate-limit tracking."""

import os
import re
import json
import time
from typing import List, Dict, Any, Optional
import requests

from engine.config import GEMINI_API_KEY, GEMINI_MODEL

# Ordered list of high-throughput candidate models
DEFAULT_MODELS: List[str] = [
    "gemini-flash-latest",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
]


class GeminiClient:
    """Robust Gemini API client supporting automatic multi-model failover."""

    def __init__(self, api_key: str = GEMINI_API_KEY, preferred_model: str = GEMINI_MODEL):
        self.api_key = api_key.strip() if api_key else ""
        
        # Build priority model list starting with configured/preferred model
        raw_env_models = os.getenv("GEMINI_MODELS", "")
        if raw_env_models:
            custom_list = [m.strip() for m in raw_env_models.split(",") if m.strip()]
        else:
            custom_list = []

        pool = []
        if preferred_model:
            pool.append(preferred_model)
        pool.extend(custom_list)
        pool.extend(DEFAULT_MODELS)

        # Deduplicate while preserving priority order
        seen = set()
        self.models: List[str] = [m for m in pool if m and not (m in seen or seen.add(m))]
        
        # Cooldown map: model_name -> timestamp until which model is paused
        self._cooldowns: Dict[str, float] = {}

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    def _get_active_models(self) -> List[str]:
        """Return models ordered by priority, prioritizing currently non-cooling models."""
        now = time.time()
        available = []
        cooling = []

        for m in self.models:
            if self._cooldowns.get(m, 0) <= now:
                available.append(m)
            else:
                cooling.append(m)

        # If all models are cooling, try them anyway as cooldowns might be expired on server
        return available if available else self.models

    def generate_json(self, system_prompt: str, user_prompt: str, timeout: int = 25) -> Optional[Dict[str, Any]]:
        """
        Generate structured JSON with automatic model failover.
        Returns parsed dictionary, or None if all models fail.
        """
        if not self.is_configured:
            return None

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_prompt}\n\n{user_prompt}\nReturn JSON strictly matching the schema."}],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        }

        candidates = self._get_active_models()
        for model in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                resp = requests.post(url, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates_data = data.get("candidates", [])
                    if not candidates_data:
                        continue
                    text = candidates_data[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                    parsed = self._extract_json(text)
                    if parsed:
                        return parsed
                elif resp.status_code in (429, 503):
                    # Rate limit (429) or high demand (503): put model on 60s cooldown and try next model
                    print(f"[gemini_client] Model '{model}' hit status {resp.status_code} ({'rate limit' if resp.status_code == 429 else 'high demand'}). Auto-switching to next model...")
                    self._cooldowns[model] = time.time() + 60.0
                elif resp.status_code == 404:
                    self._cooldowns[model] = time.time() + 3600.0
                else:
                    print(f"[gemini_client] Model '{model}' returned HTTP {resp.status_code}: {resp.text[:150]}")
            except requests.exceptions.RequestException as e:
                print(f"[gemini_client] Request error for '{model}': {e}. Auto-switching model...")
                self._cooldowns[model] = time.time() + 30.0
            except Exception as e:
                print(f"[gemini_client] Unexpected error parsing '{model}' response: {e}")

        return None

    def generate_text(self, system_instruction: str, user_prompt: str, timeout: int = 25) -> Optional[str]:
        """
        Generate plain text outreach note with automatic model failover.
        Returns generated text, or None if all models fail.
        """
        if not self.is_configured:
            return None

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_instruction}\n\n{user_prompt}"}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
            },
        }

        candidates = self._get_active_models()
        for model in candidates:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                resp = requests.post(url, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates_data = data.get("candidates", [])
                    if not candidates_data:
                        continue
                    text = candidates_data[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                    # Strip markdown fences
                    if text.startswith("```"):
                        lines = text.splitlines()
                        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
                    clean_text = text.strip()
                    if clean_text:
                        return clean_text
                elif resp.status_code in (429, 503):
                    print(f"[gemini_client] Model '{model}' hit status {resp.status_code}. Auto-switching model...")
                    self._cooldowns[model] = time.time() + 60.0
                elif resp.status_code == 404:
                    self._cooldowns[model] = time.time() + 3600.0
            except requests.exceptions.RequestException as e:
                print(f"[gemini_client] Request error on '{model}': {e}")
                self._cooldowns[model] = time.time() + 30.0
            except Exception as e:
                print(f"[gemini_client] Unexpected error on '{model}': {e}")

        return None

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Robustly parse JSON text, handling markdown fences and surrounding text."""
        if not text:
            return None

        clean = text.strip()
        if clean.startswith("```"):
            lines = clean.splitlines()
            clean = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:]).strip()

        try:
            return json.loads(clean)
        except Exception:
            pass

        match = re.search(r"(\{.*\})", clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

        return None


# Global singleton instance
gemini_client = GeminiClient()
