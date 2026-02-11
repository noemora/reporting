"""Data preprocessing and transformation."""
import pandas as pd

from config import AppConfig
from utils import TextNormalizer


class DataPreprocessor:
    """Preprocesses and transforms ticket data."""
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def preprocess(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse dates, numeric fields, and create helper columns."""
        df = self._clean_duplicate_columns(df)
        df = self._parse_datetime_columns(df)
        df = self._parse_numeric_columns(df)
        df = self._clean_text_columns(df)
        df = self._add_temporal_columns(df)
        df = self._add_composite_columns(df)
        return df
    
    def _clean_duplicate_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate or placeholder columns."""
        if "Modulo.1" in df.columns or "Modulo.2" in df.columns:
            df = df.drop(columns=[col for col in ["Modulo.1", "Modulo.2"] if col in df.columns])
        
        if "Producto" in df.columns and "Producto.1" in df.columns:
            producto_values = df["Producto"].astype(str).str.strip().str.lower().replace("nan", "")
            producto_is_placeholder = (producto_values.eq("") | producto_values.eq("no product")).all()
            if producto_is_placeholder:
                df = df.drop(columns=["Producto"]).rename(columns={"Producto.1": "Producto"})
        
        return df
    
    def _parse_datetime_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert datetime columns to proper datetime type."""
        for col in self.config.DATETIME_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        return df
    
    def _parse_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert numeric columns to proper numeric type."""
        for col in self.config.NUMERIC_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    
    def _clean_text_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean text-based columns."""
        text_columns = ["Grupo", "Tipo", "Ambiente", "Estado", "Estado de resolucion", "Modulo"]
        for col in text_columns:
            if col in df.columns:
                df[col] = TextNormalizer.clean_text_series(df[col])
        return df
    
    def _add_temporal_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add temporal helper columns."""
        if "Hora de creacion" in df.columns:
            df["Año"] = df["Hora de creacion"].dt.year
            df["Mes"] = df["Hora de creacion"].dt.month
            df["Mes Nombre"] = df["Mes"].map(self.config.MONTH_NAMES_ES)
            df["Mes Orden"] = df["Mes"]
            df["Periodo"] = df["Hora de creacion"].dt.to_period("M").dt.to_timestamp()
        return df
    
    def _add_composite_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add composite/derived columns."""
        if "Responsable Tk" in df.columns and "Agente" in df.columns:
            df["Agente/Responsable"] = df["Responsable Tk"].where(
                df["Responsable Tk"].notna() & (df["Responsable Tk"].astype(str).str.strip() != ""),
                df["Agente"],
            )
        return df
