"""KPI calculation functionality."""
from typing import Dict, Optional
import pandas as pd

from config import AppConfig


class KPICalculator:
    """Calculates key performance indicators."""
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def calculate_kpis(
        self, total_df: pd.DataFrame, resolved_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """Compute main KPI metrics."""
        total = int(total_df["ID del ticket"].nunique())
        
        source = resolved_df if resolved_df is not None else total_df
        resolved_mask = self._build_resolved_mask(source)
        resolved = int(source.loc[resolved_mask, "ID del ticket"].nunique())
        
        resolution_rate = (resolved / total) if total else 0.0
        
        return {
            "total": total,
            "resolved": resolved,
            "resolution_rate": resolution_rate,
        }
    
    def _build_resolved_mask(self, df: pd.DataFrame) -> pd.Series:
        """Build boolean mask for resolved tickets."""
        return (
            df["Estado de resolucion"].astype(str).str.lower().isin(self.config.RESOLVED_STATES)
            | df["Estado"].astype(str).str.lower().isin(self.config.RESOLVED_STATES)
        )
