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
        selected_year, selected_client = self._render_filters(df)
        
        # Apply filters
        base_filtered = self._apply_type_filters(
            df,
            selected_client,
            selected_year,
            ["Consulta de informacion", "Incidencia"],
        )
        filtered = base_filtered

        # Filter production environment
        filtered_prod = self.filter.filter_production_environment(filtered)

        st.header("KPIs - Consulta de Informacion e Incidencias")

        if filtered.empty:
            st.warning("No hay datos para Consulta de Informacion e Incidencias con los filtros seleccionados.")
        else:
            # Render missing fields
            self.ui_renderer.render_missing_fields_expander(filtered_prod, filtered)

            # Render analysis sections
            self._render_incidents_table(filtered_prod, df, selected_client, selected_year)
            self._render_resolucion_section(filtered_prod, df, selected_client, selected_year)
            self._render_modulo_section(filtered_prod, selected_year)
            self._render_ambiente_section(filtered, selected_year)
            self._render_estado_section(filtered_prod, selected_year)

        cambio_filtered = self._apply_type_filters(
            df, selected_client, selected_year, ["Cambio", "Interno"]
        )

        st.header("KPIs - Solicitudes de Cambio y Mejoras Tecnicas")

        if cambio_filtered.empty:
            st.warning("No hay datos para Solicitudes de Cambio/Mejoras Tecnicas con los filtros seleccionados.")
        else:
            self._render_modulo_section(cambio_filtered, selected_year)
            self._render_estado_section(cambio_filtered, selected_year)
    
    def _render_filters(self, df: pd.DataFrame) -> tuple:
        """Render filter controls and return selections."""
        col1, col2 = st.columns(2)
        
        with col1:
            year_options = sorted(df["Año"].dropna().unique())
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
        
        return selected_year, selected_client
    
    def _apply_type_filters(
        self,
        df: pd.DataFrame,
        selected_client: str,
        selected_year: Optional[int],
        types: List[str],
    ) -> pd.DataFrame:
        """Apply client, year, and ticket type filters."""
        filtered = self.filter.filter_by_client(df, selected_client)
        filtered = self.filter.filter_by_year(filtered, selected_year)
        filtered = self.filter.filter_by_types(filtered, types)
        return filtered
    
    def _render_incidents_table(
        self, filtered_prod: pd.DataFrame, df: pd.DataFrame, selected_client: str, selected_year: Optional[int]
    ) -> None:
        """Render the incidents and consultation table."""
        st.subheader("Flujo de tickets")
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
    
    def _render_estado_section(self, filtered_prod: pd.DataFrame, selected_year: Optional[int]) -> None:
        """Render estado (status) analysis section."""
        st.subheader("Conteo por estado")
        if filtered_prod.empty:
            st.warning("No hay datos para Conteo por estado con los filtros seleccionados.")
            return
        pivot = self.table_builder.build_pivot_table(filtered_prod, "Estado", "Sin estado")
        st.dataframe(pivot, use_container_width=True)
        self.chart_renderer.render_trend_chart(
            filtered_prod, "Estado", selected_year
        )
    
    def _render_modulo_section(self, filtered_prod: pd.DataFrame, selected_year: Optional[int]) -> None:
        """Render modulo (module) analysis section."""
        st.subheader("Conteo por módulo")
        if filtered_prod.empty:
            st.warning("No hay datos para Conteo por módulo con los filtros seleccionados.")
            return
        pivot = self.table_builder.build_pivot_table(filtered_prod, "Modulo", "Sin módulo")
        st.dataframe(pivot, use_container_width=True)
        self.chart_renderer.render_trend_chart(
            filtered_prod, "Modulo", selected_year
        )
    
    def _render_ambiente_section(self, filtered: pd.DataFrame, selected_year: Optional[int]) -> None:
        """Render ambiente (environment) analysis section."""
        st.subheader("Conteo por ambiente")
        if filtered.empty:
            st.warning("No hay datos para Conteo por ambiente con los filtros seleccionados.")
            return
        pivot = self.table_builder.build_pivot_table(filtered, "Ambiente", "Sin ambiente")
        st.dataframe(pivot, use_container_width=True)
        self.chart_renderer.render_trend_chart(
            filtered, "Ambiente", selected_year
        )
    
    def _render_resolucion_section(self, filtered_prod: pd.DataFrame, df: pd.DataFrame, selected_client: str, selected_year: Optional[int]) -> None:
        """Render resolucion (resolution) analysis section."""
        st.subheader("Conteo por SLA")
        
        # Build SLA data without year of creation filter
        sla_base = self.filter.filter_by_client(df, selected_client)
        sla_base = self.filter.filter_by_types(sla_base, ["Consulta de informacion", "Incidencia"])
        sla_base = self.filter.filter_resolved_by_year(sla_base, selected_year)
        sla_prod = self.filter.filter_production_environment(sla_base)
        
        if sla_prod.empty:
            st.warning("No hay datos para Conteo por SLA con los filtros seleccionados.")
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
        
        # Show SLA compliant ticket detail
        # Filter only SLA compliant tickets (Within SLA)
        sla_compliant_mask = sla_prod["Estado de resolucion"].astype(str).str.strip().str.lower() == "within sla"
        
        sla_data = sla_prod[sla_compliant_mask].copy()
        if not sla_data.empty:
            sla_data["Mes"] = pd.to_datetime(sla_data["Hora de resolucion"], errors="coerce").dt.month
            total_compliant = len(sla_data)
            month_order = list(range(1, 13))
            
            with st.expander(f"Ver detalle de tickets cumplidos ({total_compliant} tickets)"):
                for month in month_order:
                    month_tickets = sla_data[sla_data["Mes"] == month]["ID del ticket"].dropna().unique()
                    if len(month_tickets) > 0:
                        month_name = self.config.MONTH_NAMES_ES.get(month, str(month))
                        st.write(f"**{month_name}** ({len(month_tickets)} tickets):")
                        st.write(sorted(month_tickets.tolist()))
