"""Freshdesk API client with pagination support."""
from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Dict, Iterator, Optional

import requests

from config import AppConfig


class FreshdeskClient:
    """Client dedicated to ticket retrieval from Freshdesk API v2."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.session = requests.Session()
        self.session.auth = (config.FRESHDESK_API_KEY or "", "X")

    def iter_tickets(self, updated_since: Optional[datetime] = None) -> Iterator[Dict]:
        """Yield tickets page by page until Freshdesk returns an empty page."""
        page = 1
        while True:
            params = {
                "per_page": self.config.FRESHDESK_PER_PAGE,
                "page": page,
            }
            if updated_since is not None:
                params["updated_since"] = self._to_iso_utc(updated_since)

            response = self.session.get(
                f"{self.config.freshdesk_base_url}/tickets",
                params=params,
                timeout=self.config.FRESHDESK_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            tickets = response.json()
            if not tickets:
                break

            for ticket in tickets:
                yield ticket

            page += 1
            time.sleep(self.config.FRESHDESK_RATE_LIMIT_DELAY_SECONDS)

    @staticmethod
    def _to_iso_utc(value: datetime) -> str:
        """Convert datetime into Freshdesk-compatible UTC timestamp."""
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
