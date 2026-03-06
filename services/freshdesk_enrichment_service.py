"""Enrich Freshdesk ticket dataframe with reference entities and survey data."""
from __future__ import annotations

from typing import Dict, Iterable, Optional

import pandas as pd

from config import AppConfig
from datasources import FreshdeskClient


class FreshdeskEnrichmentService:
    """Resolves IDs to human-readable labels and augments survey-related fields."""

    def __init__(self, config: AppConfig, client: FreshdeskClient):
        self.config = config
        self.client = client

    def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enrich incoming dataframe with agents, groups, contacts, and survey ratings."""
        if df.empty:
            return df

        enriched = df.copy()
        enriched = self._enrich_agents(enriched)
        enriched = self._enrich_groups(enriched)
        enriched = self._enrich_contacts(enriched)
        enriched = self._enrich_satisfaction(enriched)
        return enriched

    def _enrich_agents(self, df: pd.DataFrame) -> pd.DataFrame:
        if "Agente" not in df.columns:
            return df

        agent_map = self._build_agent_map(self.client.iter_agents())
        if not agent_map:
            return df

        agent_ids = pd.to_numeric(df["Agente"], errors="coerce").astype("Int64")
        mapped = agent_ids.map(agent_map)
        df["Agente"] = mapped.fillna(df["Agente"])
        return df

    def _enrich_groups(self, df: pd.DataFrame) -> pd.DataFrame:
        if "Grupo" not in df.columns:
            return df

        group_map = self._build_group_map(self.client.iter_groups())
        if not group_map:
            return df

        group_ids = pd.to_numeric(df["Grupo"], errors="coerce").astype("Int64")
        mapped = group_ids.map(group_map)
        df["Grupo"] = mapped.fillna(df["Grupo"])
        return df

    def _enrich_contacts(self, df: pd.DataFrame) -> pd.DataFrame:
        if "ID del contacto" not in df.columns or "Nombre completo" not in df.columns:
            return df

        missing_mask = df["Nombre completo"].isna() | (df["Nombre completo"].astype("string").str.strip() == "")
        if not missing_mask.any():
            return df

        missing_contact_ids = (
            pd.to_numeric(df.loc[missing_mask, "ID del contacto"], errors="coerce")
            .dropna()
            .astype(int)
            .unique()
            .tolist()
        )
        if not missing_contact_ids:
            return df

        contact_map = self._build_contact_map(self.client.iter_contacts(set(missing_contact_ids)))
        if not contact_map:
            return df

        contact_ids = pd.to_numeric(df["ID del contacto"], errors="coerce").astype("Int64")
        mapped_names = contact_ids.map(contact_map)
        df.loc[missing_mask, "Nombre completo"] = mapped_names[missing_mask].fillna(df.loc[missing_mask, "Nombre completo"])
        return df

    def _enrich_satisfaction(self, df: pd.DataFrame) -> pd.DataFrame:
        if "ID del ticket" not in df.columns:
            return df

        ratings = list(self.client.iter_satisfaction_ratings())
        if not ratings:
            return df

        survey_map = self._build_survey_map(ratings)
        if not survey_map:
            return df

        ticket_ids = pd.to_numeric(df["ID del ticket"], errors="coerce").astype("Int64")
        survey_series = ticket_ids.map(survey_map)

        if "Resultados de la encuesta" in df.columns:
            df["Resultados de la encuesta"] = survey_series.map(
                lambda value: value.get("resultado") if isinstance(value, dict) else pd.NA
            ).fillna(df["Resultados de la encuesta"])

        if "El estado de cada respuesta" in df.columns:
            df["El estado de cada respuesta"] = survey_series.map(
                lambda value: value.get("estado") if isinstance(value, dict) else pd.NA
            ).fillna(df["El estado de cada respuesta"])

        return df

    @staticmethod
    def _build_agent_map(agents: Iterable[Dict]) -> Dict[int, str]:
        mapping: Dict[int, str] = {}
        for agent in agents:
            agent_id = agent.get("id")
            if not isinstance(agent_id, int):
                continue
            contact = agent.get("contact") or {}
            name = contact.get("name") or agent.get("name")
            if name:
                mapping[agent_id] = str(name)
        return mapping

    @staticmethod
    def _build_group_map(groups: Iterable[Dict]) -> Dict[int, str]:
        mapping: Dict[int, str] = {}
        for group in groups:
            group_id = group.get("id")
            if not isinstance(group_id, int):
                continue
            name = group.get("name")
            if name:
                mapping[group_id] = str(name)
        return mapping

    @staticmethod
    def _build_contact_map(contacts: Iterable[Dict]) -> Dict[int, str]:
        mapping: Dict[int, str] = {}
        for contact in contacts:
            contact_id = contact.get("id")
            if not isinstance(contact_id, int):
                continue
            name = contact.get("name")
            if name:
                mapping[contact_id] = str(name)
        return mapping

    @staticmethod
    def _build_survey_map(ratings: Iterable[Dict]) -> Dict[int, Dict[str, Optional[str]]]:
        mapping: Dict[int, Dict[str, Optional[str]]] = {}
        for rating in ratings:
            ticket_id = rating.get("ticket_id")
            if not isinstance(ticket_id, int):
                continue

            numeric_value = rating.get("rating")
            answer_text = rating.get("feedback") or rating.get("comment")
            status = rating.get("status") or rating.get("survey_status")

            if numeric_value is None and answer_text is None and status is None:
                continue

            if numeric_value is not None and answer_text:
                resultado = f"{numeric_value} - {answer_text}"
            elif numeric_value is not None:
                resultado = str(numeric_value)
            else:
                resultado = str(answer_text)

            mapping[ticket_id] = {
                "resultado": resultado,
                "estado": str(status) if status is not None else None,
            }
        return mapping
