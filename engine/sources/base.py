"""Base adapter class for job sources."""

import time
import requests
from typing import List, Optional
from engine.models import NormalizedListing


class BaseSourceAdapter:
    source_name: str = "base"
    timeout_seconds: int = 20
    max_retries: int = 2

    def fetch(self) -> List[NormalizedListing]:
        """Fetch raw jobs and return normalized listings."""
        raise NotImplementedError

    def _http_get(self, url: str, headers: Optional[dict] = None, params: Optional[dict] = None) -> Optional[dict | list]:
        req_headers = {"User-Agent": "AutoBotLinkedInJob/3.0"}
        if headers:
            req_headers.update(headers)

        for attempt in range(1, self.max_retries + 2):
            try:
                resp = requests.get(url, headers=req_headers, params=params, timeout=self.timeout_seconds)
                if resp.status_code == 200:
                    return resp.json()
                print(f"[{self.source_name}] Attempt {attempt}: Received HTTP {resp.status_code}")
            except Exception as e:
                print(f"[{self.source_name}] Attempt {attempt} failed: {e}")
            if attempt <= self.max_retries:
                time.sleep(1.5 * attempt)
        return None

    def _http_post(self, url: str, json_data: dict, headers: Optional[dict] = None) -> Optional[dict]:
        req_headers = {
            "User-Agent": "AutoBotLinkedInJob/3.0",
            "Content-Type": "application/json"
        }
        if headers:
            req_headers.update(headers)

        for attempt in range(1, self.max_retries + 2):
            try:
                resp = requests.post(url, headers=req_headers, json=json_data, timeout=self.timeout_seconds)
                if resp.status_code == 200:
                    return resp.json()
                print(f"[{self.source_name}] Attempt {attempt}: Received HTTP {resp.status_code} - {resp.text[:200]}")
            except Exception as e:
                print(f"[{self.source_name}] Attempt {attempt} failed: {e}")
            if attempt <= self.max_retries:
                time.sleep(1.5 * attempt)
        return None
