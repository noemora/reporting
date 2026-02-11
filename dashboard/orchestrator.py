"""Dashboard orchestration and coordination."""
from typing import List, Optional
import pandas as pd
import streamlit as st

from config import AppConfig
from data import DataFilter
from services import KPICalculator, TableBuilder
from ui import ChartRenderer, UIRenderer


class DashboardOrchestrator:
    """Orchestrates the entire dashboard rendering process."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.filter = DataFilter(config)
        self.kpi_calculator = KPICalculator(config)
        self.table_builder = TableBuilder(config)
        self.chart_renderer = ChartRenderer(config)
        self.ui_renderer = UIRenderer()
    
    def render_dashboard(self, df: pd.DataFrame) -> None:
        """Render complete hybrid dashboard."""
        card_placeholder = st.container()
        
        # Render filters
        st.subheader("Filtros")
        selected_year, selected_client, tipos = self._render_filters(df)
        
        # Apply filters
        base_filtered = self._apply_base_filters(df, selected_client, tipos)
        filtered = self.filter.filter_by_year(base_filtered, selected_year)
        
        if filtered.empty:
            st.warning("No hay datos para los filtros seleccionados.")
            return
        
        # Render KPI cards
        with card_placeholder:
            resolved_df = self.filter.filter_resolved_by_year(base_filtered, selected_year)
            kpis = self.kpi_calculator.calculate_kpis(filtered, resolved_df)
            self.ui_renderer.render_kpi_cards(kpis)
        
        # Filter production environment
        filtered_prod = self.filter.filter_production_environment(filtered)
        
        # Render incidents table
        st.subheader("Incidentes y consulta de informacion")
        self._render_incidents_table(filtered_prod, base_filtered, selected_year)
        
        # Render missing fields
        self.ui_renderer.render_missing_fields_expander(filtered_prod, filtered)
        
        # Render analysis sections
        self._render_estado_section(filtered_prod, selected_year)
        self._render_modulo_section(filtered_prod, selected_year)
        self._render_ambiente_section(filtered, selected_year)
        self._render_resolucion_section(filtered_prod, selected_year)
    
    def _render_filters(self, df: pd.DataFrame) -> tuple:
        """Render filter controls and return selections."""
        col1, col2, col3 = st.columns(3)
        
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
        
        with col3:
            tipos = st.multiselect(
                "Tipo",
                sorted(df["Tipo"].dropna().unique()),
                key="hybrid_tipo",
            )
        
        return selected_year, selected_client, tipos
    
    def _apply_base_filters(
        self, df: pd.DataFrame, selected_client: str, tipos: List[str]
    ) -> pd.DataFrame:
        """Apply base filters (client and types)."""
        filtered = self.filter.filter_by_client(df, selected_client)
        filtered = self.filter.filter_by_types(filtered, tipos)
        return filtered
    
    def _render_incidents_table(
        self, filtered_prod: pd.DataFrame, base_filtered: pd.DataFrame, selected_year: Optional[int]
    ) -> None:
        """Render the incidents and consultation table."""
        filtered_prod = filtered_prod.dropna(subset=["Hora de creacion"])
        month_order = list(range(1, 13))
        
        # Created counts
        created_counts = (
            filtered_prod.groupby(filtered_prod["Hora de creacion"].dt.month)["ID del ticket"]
            .nunique()
            .reindex(month_order, fill_value=0)
        )
        
        # Resolved counts
        resolved_base = self.filter.filter_resolved_by_year(base_filtered, selected_year)
        resolved_prod = self.filter.filter_production_environment(resolved_base)
        resolved_mask = self.kpi_calculator._build_resolved_mask(resolved_prod)
        
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
        pivot = self.table_builder.build_pivot_table(filtered_prod, "Estado", "Sin estado")
        st.dataframe(pivot, use_container_width=True)
        self.chart_renderer.render_trend_chart(
            filtered_prod, "Estado", selected_year, "Tendencia de estado por mes"
        )
    
    def _render_modulo_section(self, filtered_prod: pd.DataFrame, selected_year: Optional[int]) -> None:
        """Render modulo (module) analysis section."""
        st.subheader("Conteo por módulo")
        pivot = self.table_builder.build_pivot_table(filtered_prod, "Modulo", "Sin módulo")
        st.dataframe(pivot, use_container_width=True)
        self.chart_renderer.render_trend_chart(
            filtered_prod, "Modulo", selected_year, "Tendencia de módulo por mes"
        )
    
    def _render_ambiente_section(self, filtered: pd.DataFrame, selected_year: Optional[int]) -> None:
        """Render ambiente (environment) analysis section."""
        st.subheader("Conteo por ambiente")
        pivot = self.table_builder.build_pivot_table(filtered, "Ambiente", "Sin ambiente")
        st.dataframe(pivot, use_container_width=True)
        self.chart_renderer.render_trend_chart(
            filtered, "Ambiente", selected_year, "Tendencia de ambiente por mes"
        )
    
    def _render_resolucion_section(self, filtered_prod: pd.DataFrame, selected_year: Optional[int]) -> None:
        """Render resolucion (resolution) analysis section."""
        st.subheader("Conteo por estado de resolución")
        pivot = self.table_builder.build_pivot_table(
            filtered_prod, "Estado de resolucion", "Sin estado de resolución"
        )
        pivot = self.table_builder.add_sla_percentage_row(pivot)
        st.dataframe(pivot, use_container_width=True)
        self.chart_renderer.render_trend_chart(
            filtered_prod, "Estado de resolucion", selected_year, "Tendencia de estado de resolución por mes"
        )
