"""Map Freshdesk ticket payloads to app column schema."""
from __future__ import annotations

from typing import Dict, List

import pandas as pd

from config import AppConfig


class FreshdeskTicketMapper:
    """Transforms Freshdesk JSON tickets into DataFrame rows for REQUIRED_COLUMNS."""

    def __init__(self, config: AppConfig):
        self.config = config

    def to_dataframe(self, tickets: List[Dict]) -> pd.DataFrame:
        """Convert a list of Freshdesk tickets into a schema-aligned DataFrame."""
        rows = [self._map_ticket(ticket) for ticket in tickets]
        if not rows:
            return pd.DataFrame(columns=self.config.REQUIRED_COLUMNS)
        return pd.DataFrame(rows, columns=self.config.REQUIRED_COLUMNS)

    def _map_ticket(self, ticket: Dict) -> Dict:
        row = {column: pd.NA for column in self.config.REQUIRED_COLUMNS}

        status_label = self.config.FRESHDESK_STATUS_MAP.get(ticket.get("status"), ticket.get("status"))

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
        row["Hora de resolucion"] = ticket.get("resolved_at")
        row["Hora de cierre"] = ticket.get("closed_at")
        row["Hora de Ultima actualizacion"] = ticket.get("updated_at")
        row["Estado de resolucion"] = (
            "resuelto" if str(status_label).strip().lower() in self.config.RESOLVED_STATES else "pendiente"
        )
        row["Etiquetas"] = ", ".join(ticket.get("tags", [])) if ticket.get("tags") else pd.NA
        row["ID del contacto"] = ticket.get("requester_id")
        row["Nombre completo"] = ticket.get("requester_name")

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
