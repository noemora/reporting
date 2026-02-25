"""Base runtime for dashboard section renderers."""
from typing import Callable, List, Tuple

import pandas as pd

from config import AppConfig
from data import DataFilter
from services import TableBuilder
from ui import ChartRenderer
from utils import format_numeric_display_table, resolve_comparison_years


class SectionRendererBase:
    """Shared runtime helpers for section renderers."""

    def __init__(
        self,
        config: AppConfig,
        data_filter: DataFilter,
        table_builder: TableBuilder,
        chart_renderer: ChartRenderer,
    ):
        self.config = config
        self.filter = data_filter
        self.table_builder = table_builder
        self.chart_renderer = chart_renderer
        self._build_widget_key: Callable[..., str]
        self._render_table_in_details_expander: Callable[[pd.DataFrame, str], None]
        self._export_charts: List[Tuple[str, object]]
        self._build_resolved_mask: Callable[[pd.DataFrame], pd.Series]
        self._build_estado_grouped: Callable[[pd.DataFrame, str], pd.DataFrame]
        self._normalize_resolution_status_for_display: Callable[[pd.Series], pd.Series]

    def set_runtime(
        self,
        build_widget_key: Callable[..., str],
        render_table_in_details_expander: Callable[[pd.DataFrame, str], None],
        export_charts: List[Tuple[str, object]],
        build_resolved_mask: Callable[[pd.DataFrame], pd.Series],
        build_estado_grouped: Callable[[pd.DataFrame, str], pd.DataFrame],
        normalize_resolution_status_for_display: Callable[[pd.Series], pd.Series],
    ) -> None:
        self._build_widget_key = build_widget_key
        self._render_table_in_details_expander = render_table_in_details_expander
        self._export_charts = export_charts
        self._build_resolved_mask = build_resolved_mask
        self._build_estado_grouped = build_estado_grouped
        self._normalize_resolution_status_for_display = normalize_resolution_status_for_display

    @staticmethod
    def _year_window(selected_year):
        return resolve_comparison_years(selected_year)

    @staticmethod
    def _format_table(
        table: pd.DataFrame,
        *,
        coerce_numeric: bool = True,
        replace_comma_with_dot: bool = True,
    ) -> pd.DataFrame:
        return format_numeric_display_table(
            table,
            coerce_numeric=coerce_numeric,
            replace_comma_with_dot=replace_comma_with_dot,
        )

    def _append_export_chart(self, label: str, chart_fig: object) -> None:
        if chart_fig is not None:
            self._export_charts.append((label, chart_fig))
