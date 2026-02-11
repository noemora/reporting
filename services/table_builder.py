"""Table building functionality."""
import pandas as pd

from config import AppConfig


class TableBuilder:
    """Builds various data tables for analysis."""
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def build_monthly_counts_table(
        self, created_counts: pd.Series, resolved_counts: pd.Series
    ) -> pd.DataFrame:
        """Build incidents and consultation table."""
        month_order = list(range(1, 13))
        table = pd.DataFrame(
            {
                self.config.MONTH_NAMES_ES[m]: [created_counts.get(m, 0), resolved_counts.get(m, 0)]
                for m in month_order
            },
            index=["Tickets enviados por cliente", "Tickets atendidos por N5"],
        )
        table.index.name = "Recepcion/atencion de tickets"
        table = table.fillna(0)
        table["Total"] = table.sum(axis=1)
        return table
    
    def build_pivot_table(
        self, df: pd.DataFrame, index_col: str, fill_missing: str = "Sin valor"
    ) -> pd.DataFrame:
        """Build a generic pivot table by month."""
        df = df.copy()
        df[index_col] = df[index_col].fillna(fill_missing)
        
        month_order = list(range(1, 13))
        pivot = (
            df.pivot_table(
                index=index_col,
                columns="Mes",
                values="ID del ticket",
                aggfunc="nunique",
                fill_value=0,
            ).sort_index()
        )
        
        pivot = pivot.reindex(columns=month_order, fill_value=0)
        pivot.columns = [self.config.MONTH_NAMES_ES.get(m, str(m)) for m in pivot.columns]
        pivot["Total"] = pivot.sum(axis=1)
        pivot.loc["Total"] = pivot.sum(axis=0)
        
        return pivot
    
    def add_sla_percentage_row(self, pivot: pd.DataFrame) -> pd.DataFrame:
        """Add SLA violated percentage row to resolution table."""
        pivot = pivot.copy()
        resolucion_index = pivot.index.astype(str).str.lower()
        violated_mask = resolucion_index.str.contains("sla") & resolucion_index.str.contains("violat")
        
        if not violated_mask.any():
            return pivot
        
        violated_row = pivot.loc[violated_mask].iloc[0]
        month_cols = [col for col in pivot.columns if col != "Total"]
        totals_by_col = pivot[month_cols].sum(axis=0)
        totals_all = totals_by_col.sum()
        
        percent_row = (violated_row[month_cols] / totals_by_col.replace(0, pd.NA))
        percent_total = (violated_row[month_cols].sum() / totals_all) if totals_all else 0
        
        percent_values = [
            f"{value * 100:.1f}%" if pd.notna(value) else "0.0%"
            for value in percent_row.values
        ]
        percent_values.append(f"{percent_total * 100:.1f}%")
        pivot.loc["SLA violated %"] = percent_values
        
        return pivot
