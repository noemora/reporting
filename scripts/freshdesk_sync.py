"""CLI entrypoint for Freshdesk synchronization."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from config import AppConfig
from services.freshdesk_sync_service import FreshdeskSyncService


def _load_dotenv_if_present() -> None:
    """Load .env values when they are not already present in process env."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _build_config_from_env() -> AppConfig:
    _load_dotenv_if_present()
    config = AppConfig()
    config.FRESHDESK_DOMAIN = os.getenv("FRESHDESK_DOMAIN", config.FRESHDESK_DOMAIN)
    config.FRESHDESK_API_KEY = os.getenv("FRESHDESK_API_KEY", config.FRESHDESK_API_KEY)
    config.FRESHDESK_BACKFILL_UPDATED_SINCE = os.getenv(
        "FRESHDESK_BACKFILL_UPDATED_SINCE", config.FRESHDESK_BACKFILL_UPDATED_SINCE
    )
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincroniza tickets de Freshdesk hacia snapshot local.")
    parser.add_argument(
        "--mode",
        choices=["backfill", "incremental"],
        default="incremental",
        help="backfill: carga completa inicial; incremental: solo cambios desde ultimo sync.",
    )
    args = parser.parse_args()

    config = _build_config_from_env()
    service = FreshdeskSyncService(config)
    result = service.sync(mode=args.mode)

    print(f"Modo: {result.mode}")
    print(f"Tickets traidos: {result.fetched_tickets}")
    print(f"Tickets totales snapshot: {result.merged_tickets}")
    print(f"Snapshot: {result.snapshot_path}")
    print(f"Estado: {result.state_path}")
    print(f"Watermark UTC: {result.watermark_utc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
