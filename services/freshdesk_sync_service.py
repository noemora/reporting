"""Freshdesk synchronization service: backfill + incremental upsert."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from typing import Dict

import pandas as pd

from config import AppConfig
from datasources import FreshdeskClient, FreshdeskTicketMapper
from .freshdesk_enrichment_service import FreshdeskEnrichmentService


@dataclass
class SyncResult:
    """Represents the result of one synchronization execution."""

    mode: str
    fetched_tickets: int
    merged_tickets: int
    snapshot_path: str
    state_path: str
    watermark_utc: str


class FreshdeskSyncService:
    """Coordinates extraction, mapping, merge, and persistence of Freshdesk tickets."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.client = FreshdeskClient(config)
        self.mapper = FreshdeskTicketMapper(config)
        self.enricher = FreshdeskEnrichmentService(config, self.client)

    def sync(self, mode: str) -> SyncResult:
        """Run a sync in `backfill` or `incremental` mode."""
        self._validate_settings()
        self.config.freshdesk_output_path.mkdir(parents=True, exist_ok=True)

        updated_since = None
        if mode == "incremental":
            updated_since = self._resolve_incremental_watermark()
        elif mode == "backfill":
            updated_since = self._resolve_backfill_start()

        tickets = list(self.client.iter_tickets(updated_since=updated_since))
        dynamic_status_map = self._build_status_map()
        incoming_df = self.mapper.to_dataframe(tickets, status_map_override=dynamic_status_map)
        incoming_df = self.enricher.enrich(incoming_df)

        merged_df = incoming_df if mode == "backfill" else self._merge_with_snapshot(incoming_df)

        if merged_df.empty:
            merged_df = pd.DataFrame(columns=self.config.REQUIRED_COLUMNS)

        if "ID del ticket" in merged_df.columns:
            merged_df = merged_df.drop_duplicates(subset=["ID del ticket"], keep="last")

        merged_df = self._normalize_schema_for_storage(merged_df)
        merged_df.to_parquet(self.config.freshdesk_snapshot_path, index=False)

        watermark_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._write_state(
            {
                "last_successful_sync_utc": watermark_utc,
                "last_mode": mode,
                "last_fetch_count": len(incoming_df),
                "last_merged_count": len(merged_df),
            }
        )

        return SyncResult(
            mode=mode,
            fetched_tickets=len(incoming_df),
            merged_tickets=len(merged_df),
            snapshot_path=str(self.config.freshdesk_snapshot_path),
            state_path=str(self.config.freshdesk_state_path),
            watermark_utc=watermark_utc,
        )

    def _merge_with_snapshot(self, incoming_df: pd.DataFrame) -> pd.DataFrame:
        """Merge incoming records with current snapshot and keep the latest per ticket ID."""
        if incoming_df.empty:
            return self._read_snapshot_or_empty()

        existing_df = self._read_snapshot_or_empty()
        merged_df = pd.concat([existing_df, incoming_df], ignore_index=True)

        if "Hora de Ultima actualizacion" in merged_df.columns:
            merged_df["Hora de Ultima actualizacion"] = pd.to_datetime(
                merged_df["Hora de Ultima actualizacion"], errors="coerce"
            )
            merged_df = merged_df.sort_values("Hora de Ultima actualizacion")

        return merged_df

    def _read_snapshot_or_empty(self) -> pd.DataFrame:
        if not self.config.freshdesk_snapshot_path.exists():
            return pd.DataFrame(columns=self.config.REQUIRED_COLUMNS)
        return pd.read_parquet(self.config.freshdesk_snapshot_path)

    def _resolve_incremental_watermark(self) -> datetime:
        state = self._read_state()
        watermark_raw = state.get("last_successful_sync_utc") if state else None

        if not watermark_raw:
            # Default lookback when state does not exist yet.
            return datetime.now(timezone.utc) - timedelta(days=30)

        parsed = datetime.fromisoformat(watermark_raw.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)

    def _resolve_backfill_start(self) -> datetime:
        """Resolve historical starting point for full backfill extraction."""
        value = self.config.FRESHDESK_BACKFILL_UPDATED_SINCE
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)

    def _read_state(self) -> Dict:
        if not self.config.freshdesk_state_path.exists():
            return {}
        with self.config.freshdesk_state_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_state(self, data: Dict) -> None:
        with self.config.freshdesk_state_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=True, indent=2)

    def _validate_settings(self) -> None:
        missing = []
        if not self.config.FRESHDESK_DOMAIN:
            missing.append("FRESHDESK_DOMAIN")
        if not self.config.FRESHDESK_API_KEY:
            missing.append("FRESHDESK_API_KEY")
        if missing:
            raise ValueError(
                "Configuracion Freshdesk incompleta. Variables faltantes: " + ", ".join(missing)
            )

    def _normalize_schema_for_storage(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column types to a stable schema before parquet persistence."""
        normalized = df.copy()

        for col in self.config.DATETIME_COLUMNS:
            if col in normalized.columns:
                normalized[col] = pd.to_datetime(normalized[col], errors="coerce", utc=True)

        for col in self.config.NUMERIC_COLUMNS:
            if col in normalized.columns:
                normalized[col] = pd.to_numeric(normalized[col], errors="coerce")

        if "ID del ticket" in normalized.columns:
            normalized["ID del ticket"] = pd.to_numeric(normalized["ID del ticket"], errors="coerce")

        text_columns = {
            col
            for col in self.config.REQUIRED_COLUMNS
            if col not in set(self.config.DATETIME_COLUMNS)
            and col not in set(self.config.NUMERIC_COLUMNS)
            and col != "ID del ticket"
        }

        for col in text_columns:
            if col in normalized.columns:
                normalized[col] = normalized[col].map(self._coerce_text_value)

        return normalized

    def _build_status_map(self) -> Dict[int, str]:
        """Build effective status map combining API metadata and local overrides."""
        api_map = self.client.get_ticket_status_map()
        return {**api_map, **self.config.FRESHDESK_STATUS_MAP}

    @staticmethod
    def _coerce_text_value(value):
        """Convert mixed values into nullable text for consistent parquet serialization."""
        if pd.isna(value):
            return pd.NA
        if isinstance(value, (dict, list, tuple, set)):
            return json.dumps(value, ensure_ascii=True)
        return str(value)
