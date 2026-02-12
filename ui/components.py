"""UI components rendering."""
from typing import List
import pandas as pd
import streamlit as st


class UIRenderer:
    """Renders UI components."""
    
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
