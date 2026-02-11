"""Data validation and standardization."""
from typing import Dict, List
import pandas as pd
import streamlit as st

from config import AppConfig
from utils import TextNormalizer


class DataValidator:
    """Validates and standardizes DataFrame columns."""
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def validate_and_standardize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize column names and warn if core columns are missing."""
        df = df.copy()
        df = df.replace(r"^\s*$", pd.NA, regex=True)
        df = df.dropna(axis=1, how="all")
        
        normalized_map = self._build_column_map(df.columns.tolist())
        rename_map = self._build_rename_map(normalized_map)
        df = df.rename(columns=rename_map)
        
        self._check_missing_core_columns(df)
        return df
    
    def _build_column_map(self, columns: List[str]) -> Dict[str, str]:
        """Map normalized names to actual column names."""
        return {TextNormalizer.normalize_column_name(col): col for col in columns}
    
    def _build_rename_map(self, normalized_map: Dict[str, str]) -> Dict[str, str]:
        """Build rename mapping for standardization."""
        rename_map = {}
        for required in self.config.REQUIRED_COLUMNS:
            key = TextNormalizer.normalize_column_name(required)
            actual = normalized_map.get(key)
            if actual is not None:
                rename_map[actual] = required
        return rename_map
    
    def _check_missing_core_columns(self, df: pd.DataFrame) -> None:
        """Check and warn about missing core columns."""
        core_columns = [
            "ID del ticket", "Estado", "Hora de creacion", "Estado de resolucion",
            "Modulo", "Ambiente", "Grupo", "Tipo",
        ]
        missing_core = [col for col in core_columns if col not in df.columns]
        if missing_core:
            st.warning(
                "Faltan columnas clave para algunos cálculos: " + ", ".join(missing_core)
            )
            with st.expander("Ver columnas detectadas"):
                st.write(sorted(df.columns.tolist()))
