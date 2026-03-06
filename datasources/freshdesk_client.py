"""Freshdesk API client with pagination support."""
from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Dict, Iterator, Optional, Set

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
        params = {
            "include": "stats,requester",
        }
        if updated_since is not None:
            params["updated_since"] = self._to_iso_utc(updated_since)
        yield from self._iter_paginated("tickets", params=params)

    def iter_agents(self) -> Iterator[Dict]:
        """Yield all active/deactivated agents visible for the API key."""
        yield from self._iter_paginated("agents")

    def iter_groups(self) -> Iterator[Dict]:
        """Yield all groups visible for the API key."""
        yield from self._iter_paginated("groups")

    def iter_contacts(self, target_ids: Optional[Set[int]] = None) -> Iterator[Dict]:
        """Yield contacts; when target_ids is provided stop early once all are found."""
        page = 1
        found_ids: Set[int] = set()

        while True:
            params = {
                "per_page": self.config.FRESHDESK_PER_PAGE,
                "page": page,
            }
            response = self.session.get(
                f"{self.config.freshdesk_base_url}/contacts",
                params=params,
                timeout=self.config.FRESHDESK_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            contacts = response.json()
            if not contacts:
                break

            for contact in contacts:
                if target_ids is None:
                    yield contact
                    continue

                contact_id = contact.get("id")
                if isinstance(contact_id, int) and contact_id in target_ids:
                    found_ids.add(contact_id)
                    yield contact

            if target_ids is not None and found_ids.issuperset(target_ids):
                break

            page += 1
            time.sleep(self.config.FRESHDESK_RATE_LIMIT_DELAY_SECONDS)

    def iter_satisfaction_ratings(self) -> Iterator[Dict]:
        """Yield satisfaction ratings from surveys endpoint."""
        yield from self._iter_paginated("surveys/satisfaction_ratings")

    def get_ticket_status_map(self) -> Dict[int, str]:
        """Return status ID to label mapping from ticket_fields metadata."""
        response = self.session.get(
            f"{self.config.freshdesk_base_url}/ticket_fields",
            timeout=self.config.FRESHDESK_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        fields = response.json()

        status_field = next((field for field in fields if field.get("name") == "status"), None)
        if not status_field:
            return {}

        choices = status_field.get("choices") or {}
        mapping: Dict[int, str] = {}
        for key, value in choices.items():
            try:
                status_id = int(key)
            except (TypeError, ValueError):
                continue

            label = None
            if isinstance(value, list) and value:
                label = value[0]
            elif isinstance(value, str):
                label = value

            if label:
                mapping[status_id] = str(label)

        return mapping

    def _iter_paginated(self, endpoint: str, params: Optional[Dict] = None) -> Iterator[Dict]:
        """Yield paginated resources from a list endpoint."""
        base_params = params.copy() if params else {}
        page = 1

        while True:
            request_params = {
                "per_page": self.config.FRESHDESK_PER_PAGE,
                "page": page,
                **base_params,
            }
            response = self.session.get(
                f"{self.config.freshdesk_base_url}/{endpoint}",
                params=request_params,
                timeout=self.config.FRESHDESK_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload:
                break

            for item in payload:
                yield item

            page += 1
            time.sleep(self.config.FRESHDESK_RATE_LIMIT_DELAY_SECONDS)

    @staticmethod
    def _to_iso_utc(value: datetime) -> str:
        """Convert datetime into Freshdesk-compatible UTC timestamp."""
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
