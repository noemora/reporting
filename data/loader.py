"""Excel data loading functionality."""
import io
import pandas as pd
import streamlit as st


class ExcelDataLoader:
    """Handles loading data from Excel files."""
    
    @staticmethod
    @st.cache_data(show_spinner=False)
    def load(file_bytes: bytes) -> pd.DataFrame:
        """Load Excel file from bytes."""
        return pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")

