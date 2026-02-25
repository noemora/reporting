"""Utilidades de render para dashboards Streamlit."""
from typing import List, Optional, Tuple

import pandas as pd


def resolve_comparison_years(selected_year: Optional[int]) -> Tuple[int, List[int]]:
    """Return current year and comparison window [year-1, year]."""
    current_year = selected_year or pd.Timestamp.today().year
    return current_year, [current_year - 1, current_year]


def format_numeric_display_table(
    table: pd.DataFrame,
    *,
    coerce_numeric: bool = True,
    replace_comma_with_dot: bool = True,
) -> pd.DataFrame:
    """Format table values for Streamlit display with locale-friendly separators."""
    display_source = table.copy()
    if coerce_numeric:
        display_source[display_source.columns] = display_source[display_source.columns].apply(
            pd.to_numeric,
            errors="coerce",
        )

    def _format_value(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            rendered = f"{value:,.0f}"
            return rendered.replace(",", ".") if replace_comma_with_dot else rendered
        return str(value)

    return display_source.apply(lambda col: col.map(_format_value))
