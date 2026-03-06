"""Excel data loading functionality."""
import io
from pathlib import Path
import pandas as pd
import streamlit as st


class ExcelDataLoader:
    """Handles loading data from Excel files."""
    
    @staticmethod
    @st.cache_data(show_spinner=False)
    def load(file_bytes: bytes) -> pd.DataFrame:
        """Load Excel file from bytes."""
        return pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")


class FreshdeskSnapshotLoader:
    """Loads Freshdesk synced snapshots from Parquet files."""

    @staticmethod
    @st.cache_data(show_spinner=False)
    def load(snapshot_path: str, snapshot_signature: float) -> pd.DataFrame:
        """Load Parquet snapshot from an absolute or relative path."""
        path = Path(snapshot_path)
        return pd.read_parquet(path)

