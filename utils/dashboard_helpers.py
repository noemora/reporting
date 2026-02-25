"""Utilidades de dominio para dashboard de tickets."""
from typing import Dict, List, Set, Tuple

import pandas as pd

from config import AppConfig
from .text_normalizer import TextNormalizer


class TicketStatusHelper:
    """Normaliza y agrupa estados de tickets y resolución."""

    def __init__(self, config: AppConfig):
        self.config = config

    def normalized_resolved_states(self) -> Set[str]:
        """Return normalized resolved states from config."""
        return {
            str(state).strip().lower()
            for state in self.config.RESOLVED_STATES
            if str(state).strip()
        }

    def normalize_estado_for_display(self, estado: pd.Series) -> pd.Series:
        """Normalize Estado values to consistent Spanish labels for display."""
        estado_raw = estado.astype("string").str.strip()
        estado_norm = (
            estado_raw.fillna("")
            .map(TextNormalizer.remove_accents)
            .str.strip()
            .str.lower()
        )

        normalized = pd.Series(pd.NA, index=estado_raw.index, dtype="object")
        resolved_states = self.normalized_resolved_states()
        normalized = normalized.mask(estado_norm.isin(resolved_states), "Resuelto")

        exact_map = {
            "pendiente": "Pendiente",
            "pending": "Pendiente",
            "abierto": "Abierto",
            "open": "Abierto",
            "nuevo": "Nuevo",
            "new": "Nuevo",
            "en progreso": "En progreso",
            "in progress": "En progreso",
            "en espera": "En espera",
            "on hold": "En espera",
            "hold": "En espera",
            "cancelado": "Cancelado",
            "cancelada": "Cancelado",
            "cancelled": "Cancelado",
            "canceled": "Cancelado",
            "reabierto": "Reabierto",
            "re-opened": "Reabierto",
            "reopened": "Reabierto",
        }
        normalized = normalized.fillna(estado_norm.map(exact_map))

        normalized = normalized.mask(
            normalized.isna() & estado_norm.str.contains(r"progreso|progress", na=False),
            "En progreso",
        )
        normalized = normalized.mask(
            normalized.isna() & estado_norm.str.contains(r"espera|waiting|hold", na=False),
            "En espera",
        )
        normalized = normalized.mask(
            normalized.isna() & estado_norm.str.contains(r"pendient|pending", na=False),
            "Pendiente",
        )
        normalized = normalized.mask(
            normalized.isna() & estado_norm.str.contains(r"cancel", na=False),
            "Cancelado",
        )
        normalized = normalized.mask(
            normalized.isna() & estado_norm.str.contains(r"reabiert|reopen", na=False),
            "Reabierto",
        )

        fallback = (
            estado_raw.map(TextNormalizer.fix_mojibake)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
            .str.title()
        )
        normalized = normalized.fillna(fallback)
        normalized = normalized.mask(normalized.isna() | normalized.eq(""), pd.NA)
        return normalized

    def build_estado_grouped(self, df: pd.DataFrame, target_col: str) -> pd.DataFrame:
        """Group all configured resolved states into 'Resuelto'."""
        grouped_df = df.copy()
        if "Estado" not in grouped_df.columns:
            grouped_df[target_col] = pd.NA
            return grouped_df

        grouped_df[target_col] = self.normalize_estado_for_display(grouped_df["Estado"])
        return grouped_df

    def build_resolved_mask(self, df: pd.DataFrame) -> pd.Series:
        """Build resolved mask using grouped Estado and Estado de resolucion."""
        resolved_states = self.normalized_resolved_states()
        grouped_df = self.build_estado_grouped(df, "Estado Agrupado")
        resolved_estado = grouped_df["Estado Agrupado"].astype(str).str.strip().str.lower().eq("resuelto")
        resolved_estado_resolucion = grouped_df["Estado de resolucion"].astype(str).str.strip().str.lower().isin(
            resolved_states
        )
        return resolved_estado | resolved_estado_resolucion

    def normalize_resolution_status_for_display(self, resolution: pd.Series) -> pd.Series:
        """Normalize Estado de resolucion values to Spanish labels for display."""
        resolution_raw = resolution.astype("string").str.strip()
        resolution_norm = (
            resolution_raw.fillna("")
            .map(TextNormalizer.remove_accents)
            .str.strip()
            .str.lower()
        )

        normalized = pd.Series(pd.NA, index=resolution_raw.index, dtype="object")
        normalized = normalized.mask(
            resolution_norm.isin({"within sla", "cumplido", "en sla", "dentro de sla"}),
            "Cumplido",
        )
        normalized = normalized.mask(
            resolution_norm.isin({"sla violated", "incumplido", "fuera de sla"}),
            "Incumplido",
        )
        normalized = normalized.mask(
            resolution_norm.isin({"resuelto", "resolved", "solucionado", "cerrado", "closed"}),
            "Resuelto",
        )

        normalized = normalized.mask(
            normalized.isna() & resolution_norm.str.contains(r"within\s*sla|dentro\s*de\s*sla", na=False),
            "Cumplido",
        )
        normalized = normalized.mask(
            normalized.isna() & resolution_norm.str.contains(r"violat|incumpl|fuera\s*de\s*sla", na=False),
            "Incumplido",
        )

        normalized = normalized.mask(
            normalized.isna() & (resolution_raw.isna() | resolution_raw.eq("")),
            "Sin estado de resolución",
        )
        fallback = (
            resolution_raw.map(TextNormalizer.fix_mojibake)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
            .str.title()
        )
        normalized = normalized.fillna(fallback)
        normalized = normalized.fillna("Sin estado de resolución")
        return normalized


class TeamFilterHelper:
    """Construye opciones de Team Asignado para filtros de dashboard."""

    def __init__(self, support_team_unified_label: str = "Soporte"):
        self.support_team_unified_label = support_team_unified_label

    @staticmethod
    def is_support_team_value(value: str) -> bool:
        """Return True when a Team Asignado value belongs to support teams."""
        raw_value = str(value).strip()
        if not raw_value:
            return False
        normalized = TextNormalizer.remove_accents(raw_value).lower()
        normalized = " ".join(normalized.split())
        return "soporte" in normalized or "support" in normalized

    def build_team_filter_config(
        self,
        df: pd.DataFrame,
        commercial_mode: bool,
    ) -> Tuple[List[str], Dict[str, List[str]]]:
        """Build Team Asignado filter options and the label-to-values map."""
        if "Team Asignado" not in df.columns:
            return [], {}

        team_values = sorted(
            {
                value
                for value in df["Team Asignado"].dropna().astype(str).str.strip()
                if str(value).strip()
            }
        )
        if not team_values:
            return [], {}

        if not commercial_mode:
            return team_values, {value: [value] for value in team_values}

        support_teams = [value for value in team_values if self.is_support_team_value(value)]
        non_support_teams = [value for value in team_values if value not in support_teams]

        options = list(non_support_teams)
        option_map = {value: [value] for value in non_support_teams}
        if support_teams:
            options.append(self.support_team_unified_label)
            option_map[self.support_team_unified_label] = support_teams

        options = sorted(
            options,
            key=lambda value: TextNormalizer.remove_accents(str(value)).lower(),
        )
        return options, option_map

    @staticmethod
    def resolve_selected_team_values(
        selected_team_labels: List[str],
        option_map: Dict[str, List[str]],
    ) -> List[str]:
        """Resolve selected Team Asignado labels into raw source values."""
        if not selected_team_labels:
            return []

        resolved_values: List[str] = []
        for label in selected_team_labels:
            resolved_values.extend(option_map.get(label, [label]))
        return list(dict.fromkeys(resolved_values))
