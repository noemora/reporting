"""Dashboard orchestration and coordination."""
from typing import List, Optional
import pandas as pd
import streamlit as st

from config import AppConfig
from data import DataFilter
from services import TableBuilder
from ui import ChartRenderer, UIRenderer


class DashboardOrchestrator:
    """Orchestrates the entire dashboard rendering process."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.filter = DataFilter(config)
        self.table_builder = TableBuilder(config)
        self.chart_renderer = ChartRenderer(config)
        self.ui_renderer = UIRenderer()
    
    def render_dashboard(self, df: pd.DataFrame) -> None:
        """Render complete hybrid dashboard."""
        # Render filters
        st.subheader("Filtros")
        selected_year, selected_client, selected_team = self._render_filters(df)
        
        # Apply filters
        base_filtered = self._apply_type_filters(
            df,
            selected_client,
            selected_year,
            selected_team,
            ["Consulta de informacion", "Incidencia"],
        )
        filtered = base_filtered

        # Filter production environment
        filtered_prod = self.filter.filter_production_environment(filtered)

        st.header("KPIs - Consulta de Informacion e Incidencias")
        st.subheader("Análisis de tickets en ambientes productivos")

        if filtered.empty:
            st.warning("No hay datos para Consulta de Informacion e Incidencias con los filtros seleccionados.")
        else:
            # Render missing fields
            # self.ui_renderer.render_missing_fields_expander(filtered_prod, filtered)

            # Render analysis sections
            self._render_incidents_table(filtered_prod, df, selected_client, selected_year, selected_team)
            self._render_team_section(filtered_prod, selected_year)
            self._render_resolucion_section(filtered_prod, df, selected_client, selected_year, selected_team)
            self._render_modulo_section(filtered_prod, selected_year)
            self._render_ambiente_section(filtered, selected_year)
            self._render_estado_section(filtered_prod, selected_year)

        cambio_filtered = self._apply_type_filters(
            df, selected_client, selected_year, selected_team, ["Cambio"]
        )

        st.header("KPIs - Solicitudes de Cambio")
        st.subheader("Análisis de tickets de TODOS los ambientes")

        if cambio_filtered.empty:
            st.warning("No hay datos para Solicitudes de Cambio con los filtros seleccionados.")
        else:
            self._render_team_section(cambio_filtered, selected_year)
            self._render_modulo_section(cambio_filtered, selected_year)
            self._render_estado_section(cambio_filtered, selected_year)

        internos_filtered = self._apply_type_filters(
            df, selected_client, selected_year, selected_team, ["Interno"]
        )

        st.header("KPIs - Solicitudes de Mejoras Técnicas")
        st.subheader("Análisis de tickets de TODOS los ambientes")

        if internos_filtered.empty:
            st.warning("No hay datos para Solicitudes de Mejoras Técnicas con los filtros seleccionados.")
        else:
            self._render_team_section(internos_filtered, selected_year)
            self._render_modulo_section(internos_filtered, selected_year)
            self._render_estado_section(internos_filtered, selected_year)
    
    def _render_filters(self, df: pd.DataFrame) -> tuple:
        """Render filter controls and return selections."""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            year_options = sorted(df["Año"].dropna().unique(), reverse=True)
            current_year = pd.Timestamp.today().year
            year_index = 0
            if year_options:
                year_index = min(
                    range(len(year_options)),
                    key=lambda idx: abs(year_options[idx] - current_year),
                )
            selected_year = (
                st.selectbox("Año", year_options, index=year_index, key="hybrid_year")
                if year_options
                else None
            )
        
        with col2:
            client_options = sorted(df["Grupo"].dropna().unique())
            selected_client = (
                st.selectbox("Cliente (Grupo)", ["Todos"] + client_options, key="hybrid_cliente")
                if client_options
                else "Todos"
            )
        
        with col3:
            team_options = sorted(df["Team Asignado"].dropna().unique())
            selected_team = (
                st.multiselect("Team Asignado", team_options, default=[], key="hybrid_team")
                if team_options
                else []
            )
        
        return selected_year, selected_client, selected_team
    
    def _apply_type_filters(
        self,
        df: pd.DataFrame,
        selected_client: str,
        selected_year: Optional[int],
        selected_team: List[str],
        types: List[str],
    ) -> pd.DataFrame:
        """Apply client, year, team, and ticket type filters."""
        filtered = self.filter.filter_by_client(df, selected_client)
        filtered = self.filter.filter_by_year(filtered, selected_year)
        filtered = self.filter.filter_by_team(filtered, selected_team)
        filtered = self.filter.filter_by_types(filtered, types)
        return filtered
    
    def _render_incidents_table(
        self, filtered_prod: pd.DataFrame, df: pd.DataFrame, selected_client: str, selected_year: Optional[int], selected_team: List[str]
    ) -> None:
        """Render the incidents and consultation table."""
        st.subheader("KPI - Flujo de tickets")
        if filtered_prod.empty:
            st.warning("No hay datos para Flujo de tickets con los filtros seleccionados.")
            return
        filtered_prod = filtered_prod.dropna(subset=["Hora de creacion"])
        month_order = list(range(1, 13))
        
        # Created counts
        created_counts = (
            filtered_prod.groupby(filtered_prod["Hora de creacion"].dt.month)["ID del ticket"]
            .nunique()
            .reindex(month_order, fill_value=0)
        )
        
        # Resolved counts - apply filters WITHOUT year of creation filter
        resolved_base = self.filter.filter_by_client(df, selected_client)
        resolved_base = self.filter.filter_by_team(resolved_base, selected_team)
        resolved_base = self.filter.filter_by_types(resolved_base, ["Consulta de informacion", "Incidencia"])
        resolved_base = self.filter.filter_resolved_by_year(resolved_base, selected_year)
        resolved_prod = self.filter.filter_production_environment(resolved_base)
        resolved_mask = (
            resolved_prod["Estado de resolucion"].astype(str).str.lower().isin(self.config.RESOLVED_STATES)
            | resolved_prod["Estado"].astype(str).str.lower().isin(self.config.RESOLVED_STATES)
        )
        
        resolved_counts = (
            resolved_prod[resolved_mask]
            .groupby(pd.to_datetime(resolved_prod["Hora de resolucion"], errors="coerce").dt.month)[
                "ID del ticket"
            ]
            .nunique()
            .reindex(month_order, fill_value=0)
        )
        
        table = self.table_builder.build_monthly_counts_table(created_counts, resolved_counts)
        st.dataframe(table, use_container_width=True)
    
    def _render_team_section(self, filtered_prod: pd.DataFrame, selected_year: Optional[int]) -> None:
        """Render team asignado analysis section."""
        st.subheader("KPI - Team Asignado")
        if filtered_prod.empty:
            st.warning("No hay datos para KPI - Team Asignado con los filtros seleccionados.")
            return
        pivot = self.table_builder.build_pivot_table(filtered_prod, "Team Asignado", "Sin team asignado")
        st.dataframe(pivot, use_container_width=True)
        self.chart_renderer.render_trend_chart(
            filtered_prod, "Team Asignado", selected_year
        )
    
    def _render_estado_section(self, filtered_prod: pd.DataFrame, selected_year: Optional[int]) -> None:
        """Render estado (status) analysis section."""
        st.subheader("KPI - Estado")
        if filtered_prod.empty:
            st.warning("No hay datos para KPI - Estado con los filtros seleccionados.")
            return
        pivot = self.table_builder.build_pivot_table(filtered_prod, "Estado", "Sin estado")
        st.dataframe(pivot, use_container_width=True)
        self.chart_renderer.render_trend_chart(
            filtered_prod, "Estado", selected_year
        )
    
    def _render_modulo_section(self, filtered_prod: pd.DataFrame, selected_year: Optional[int]) -> None:
        """Render modulo (module) analysis section."""
        st.subheader("KPI - Módulo")
        if filtered_prod.empty:
            st.warning("No hay datos para KPI - Módulo con los filtros seleccionados.")
            return
        pivot = self.table_builder.build_pivot_table(filtered_prod, "Modulo", "Sin módulo")
        if "Total" in pivot.index:
            total_row = pivot.loc[["Total"]]
            pivot = pivot.drop(index="Total").sort_values(by="Total", ascending=False)
            pivot = pd.concat([pivot, total_row])
        else:
            pivot = pivot.sort_values(by="Total", ascending=False)
        st.dataframe(pivot, use_container_width=True)
    
    def _render_ambiente_section(self, filtered: pd.DataFrame, selected_year: Optional[int]) -> None:
        """Render ambiente (environment) analysis section."""
        st.subheader("KPI - Ambiente")
        if filtered.empty:
            st.warning("No hay datos para KPI - Ambiente con los filtros seleccionados.")
            return
        pivot = self.table_builder.build_pivot_table(filtered, "Ambiente", "Sin ambiente")
        st.dataframe(pivot, use_container_width=True)
        self.chart_renderer.render_trend_chart(
            filtered, "Ambiente", selected_year
        )
    
    def _render_resolucion_section(self, filtered_prod: pd.DataFrame, df: pd.DataFrame, selected_client: str, selected_year: Optional[int], selected_team: List[str]) -> None:
        """Render resolucion (resolution) analysis section."""
        st.subheader("KPI - SLA")
        
        # Build SLA data without year of creation filter
        sla_base = self.filter.filter_by_client(df, selected_client)
        sla_base = self.filter.filter_by_team(sla_base, selected_team)
        sla_base = self.filter.filter_by_types(sla_base, ["Consulta de informacion", "Incidencia"])
        sla_base = self.filter.filter_resolved_by_year(sla_base, selected_year)
        sla_prod = self.filter.filter_production_environment(sla_base)
        
        if sla_prod.empty:
            st.warning("No hay datos para KPI - SLA con los filtros seleccionados.")
            return
        
        # Create Mes column based on resolution date for SLA table
        sla_prod = sla_prod.copy()
        sla_prod["Mes"] = pd.to_datetime(sla_prod["Hora de resolucion"], errors="coerce").dt.month
        
        # Build pivot table from all resolved tickets in selected year
        pivot = self.table_builder.build_pivot_table(
            sla_prod, "Estado de resolucion", "Sin estado de resolución"
        )
        pivot = pivot.rename(
            index={
                label: "Cumplido"
                for label in pivot.index
                if str(label).strip().lower() == "within sla"
            }
        )
        pivot = pivot.rename(
            index={
                label: "Incumplido"
                for label in pivot.index
                if str(label).strip().lower() == "sla violated"
            }
        )
        pivot = self.table_builder.add_sla_percentage_row(pivot)
        st.dataframe(pivot, use_container_width=True)
        self.chart_renderer.render_trend_chart(
            sla_prod, "Estado de resolucion", selected_year
        )
