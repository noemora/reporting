"""Map Freshdesk ticket payloads to app column schema."""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from config import AppConfig


class FreshdeskTicketMapper:
    """Transforms Freshdesk JSON tickets into DataFrame rows for REQUIRED_COLUMNS."""

    def __init__(self, config: AppConfig):
        self.config = config

    def to_dataframe(self, tickets: List[Dict], status_map_override: Optional[Dict[int, str]] = None) -> pd.DataFrame:
        """Convert a list of Freshdesk tickets into a schema-aligned DataFrame."""
        rows = [self._map_ticket(ticket, status_map_override=status_map_override) for ticket in tickets]
        if not rows:
            return pd.DataFrame(columns=self.config.REQUIRED_COLUMNS)
        return pd.DataFrame(rows, columns=self.config.REQUIRED_COLUMNS)

    def _map_ticket(self, ticket: Dict, status_map_override: Optional[Dict[int, str]] = None) -> Dict:
        row = {column: pd.NA for column in self.config.REQUIRED_COLUMNS}
        status_map = status_map_override or self.config.FRESHDESK_STATUS_MAP
        status_raw = ticket.get("status")
        status_label = status_map.get(status_raw, self.config.FRESHDESK_STATUS_MAP.get(status_raw, status_raw))

        row["ID del ticket"] = ticket.get("id")
        row["Asunto"] = ticket.get("subject")
        row["Estado"] = self._as_text(status_label)
        row["Prioridad"] = self._as_text(
            self.config.FRESHDESK_PRIORITY_MAP.get(ticket.get("priority"), ticket.get("priority"))
        )
        row["Origen"] = self._as_text(
            self.config.FRESHDESK_SOURCE_MAP.get(ticket.get("source"), ticket.get("source"))
        )
        row["Tipo"] = self._as_text(ticket.get("type"))
        row["Agente"] = ticket.get("responder_id")
        row["Grupo"] = ticket.get("group_id")
        row["Hora de creacion"] = ticket.get("created_at")
        row["Tiempo de vencimiento"] = ticket.get("due_by")
        stats = ticket.get("stats") or {}
        resolved_at = stats.get("resolved_at")
        closed_at = stats.get("closed_at")
        first_responded_at = stats.get("first_responded_at")
        row["Hora de resolucion"] = resolved_at
        row["Hora de cierre"] = closed_at
        row["Hora de Ultima actualizacion"] = ticket.get("updated_at")
        row["Estado de resolucion"] = self._sla_state(ticket.get("is_escalated"), resolved_at)
        row["Estado de primera respuesta"] = self._sla_state(ticket.get("fr_escalated"), first_responded_at)
        row["Etiquetas"] = ", ".join(ticket.get("tags", [])) if ticket.get("tags") else pd.NA
        row["ID del contacto"] = ticket.get("requester_id")
        requester = ticket.get("requester") or {}
        row["Nombre completo"] = requester.get("name") or ticket.get("requester_name")

        custom_fields = ticket.get("custom_fields") or {}
        for target_column, custom_field_name in self.config.FRESHDESK_CUSTOM_FIELD_MAPPING.items():
            if target_column in row:
                row[target_column] = custom_fields.get(custom_field_name, row[target_column])

        return row

    @staticmethod
    def _as_text(value):
        """Return nullable text for categorical fields."""
        if pd.isna(value):
            return pd.NA
        return str(value)

    @staticmethod
    def _sla_state(escalated_value, reference_timestamp):
        """Map Freshdesk SLA booleans to expected labels with empty fallback."""
        if not reference_timestamp:
            return pd.NA
        if escalated_value is True:
            return "sla violated"
        if escalated_value is False:
            return "within sla"
        return pd.NA
