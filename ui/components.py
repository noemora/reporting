"""UI components rendering."""
from typing import Dict, List
import pandas as pd
import streamlit as st


class UIRenderer:
    """Renders UI components."""
    
    @staticmethod
    def render_kpi_cards(kpis: Dict[str, float]) -> None:
        """Render KPI cards with a clean layout."""
        st.markdown(
            """
            <style>
            .kpi-card {
                background: #ffffff;
                padding: 16px;
                border-radius: 12px;
                border: 1px solid #e6e6e6;
                box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            }
            .kpi-title { font-size: 14px; color: #6b6b6b; margin-bottom: 6px; }
            .kpi-value { font-size: 24px; font-weight: 700; color: #111827; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        col1, col2, col3 = st.columns(3)
        col1.markdown(
            f"<div class='kpi-card'><div class='kpi-title'>Total tickets</div>"
            f"<div class='kpi-value'>{kpis['total']}</div></div>",
            unsafe_allow_html=True,
        )
        col2.markdown(
            f"<div class='kpi-card'><div class='kpi-title'>Tickets resueltos</div>"
            f"<div class='kpi-value'>{kpis['resolved']}</div></div>",
            unsafe_allow_html=True,
        )
        col3.markdown(
            f"<div class='kpi-card'><div class='kpi-title'>Tasa de resolución</div>"
            f"<div class='kpi-value'>{kpis['resolution_rate']:.1%}</div></div>",
            unsafe_allow_html=True,
        )
    
    @staticmethod
    def render_missing_fields_expander(
        filtered_prod: pd.DataFrame, filtered: pd.DataFrame
    ) -> None:
        """Render expander showing tickets with missing fields."""
        def get_missing_ids(df: pd.DataFrame, column: str) -> List[str]:
            values = df[column].astype(str).str.strip()
            mask = df[column].isna() | values.eq("")
            return df.loc[mask, "ID del ticket"].dropna().unique().tolist()
        
        missing_modulo = get_missing_ids(filtered_prod, "Modulo")
        missing_resolucion = get_missing_ids(filtered_prod, "Estado de resolucion")
        missing_ambiente = get_missing_ids(filtered, "Ambiente")
        missing_estado = get_missing_ids(filtered_prod, "Estado")
        
        with st.expander("Detalle de tickets con campos vacíos"):
            if missing_estado:
                st.write("Estado (productivo):", missing_estado)
            if missing_modulo:
                st.write("Módulo (productivo):", missing_modulo)
            if missing_resolucion:
                st.write("Estado de resolución (productivo):", missing_resolucion)
            if missing_ambiente:
                st.write("Ambiente:", missing_ambiente)
