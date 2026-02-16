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
        
        with st.expander("Detalle de tickets con campos vacíos"):
            if missing_modulo:
                st.write("Módulo (productivo):", missing_modulo)
