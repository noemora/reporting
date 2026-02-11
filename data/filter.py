"""Data filtering functionality."""
from typing import List, Optional
import pandas as pd

from config import AppConfig
from utils import TextNormalizer


class DataFilter:
    """Filters ticket data based on various criteria."""
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def filter_by_year(self, df: pd.DataFrame, year: Optional[int]) -> pd.DataFrame:
        """Filter data by year."""
        if year is None or "Año" not in df.columns:
            return df
        return df[df["Año"] == year]
    
    def filter_by_client(self, df: pd.DataFrame, client: str) -> pd.DataFrame:
        """Filter data by client/group."""
        if not client or client == "Todos" or "Grupo" not in df.columns:
            return df
        return df[df["Grupo"] == client]
    
    def filter_by_types(self, df: pd.DataFrame, types: List[str]) -> pd.DataFrame:
        """Filter data by ticket types."""
        if not types or "Tipo" not in df.columns:
            return df
        return df[df["Tipo"].isin(types)]
    
    def filter_production_environment(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter data for production environments only."""
        if "Ambiente" not in df.columns:
            return df
        ambiente_norm = df["Ambiente"].apply(TextNormalizer.normalize_environment)
        return df[ambiente_norm.isin(self.config.PROD_ENVIRONMENTS)].copy()
    
    def filter_resolved_by_year(self, df: pd.DataFrame, year: Optional[int]) -> pd.DataFrame:
        """Filter resolved tickets by resolution year."""
        if year is None or "Hora de resolucion" not in df.columns:
            return df
        return df[pd.to_datetime(df["Hora de resolucion"], errors="coerce").dt.year == year]
