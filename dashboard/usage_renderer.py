"""Usage table rendering for dashboard logins data."""
from typing import Callable, List, Optional, Tuple

import pandas as pd
import streamlit as st

from config import AppConfig
from ui import ChartRenderer
from utils import TextNormalizer, format_numeric_display_table, resolve_comparison_years


class UsageRenderer:
    """Renderiza la sección de usabilidad (logins) con responsabilidad aislada."""

    def __init__(self, config: AppConfig, chart_renderer: ChartRenderer):
        self.config = config
        self.chart_renderer = chart_renderer

    def render_usage_table(
        self,
        usage_df: Optional[pd.DataFrame],
        selected_year: Optional[int],
        selected_client: List[str],
        build_widget_key: Callable[..., str],
        render_table_in_details_expander: Callable[[pd.DataFrame, str], None],
        export_charts: List[Tuple[str, object]],
    ) -> Optional[pd.DataFrame]:
        """Render the platform usage table from the logins Excel."""
        st.header("Usabilidad - Actividad en la plataforma")
        if usage_df is None or usage_df.empty:
            st.info("No hay datos de logins para mostrar.")
            return None

        def resolve_column(df: pd.DataFrame, target: str) -> Optional[str]:
            for col in df.columns:
                if col.strip().lower() == target:
                    return col
            return None

        col_cliente = resolve_column(usage_df, "cliente")
        col_logins = resolve_column(usage_df, "logins")
        col_mes = resolve_column(usage_df, "mes")
        col_anio = resolve_column(usage_df, "año") or resolve_column(usage_df, "anio")

        missing_cols = [
            name
            for name, col in [
                ("cliente", col_cliente),
                ("Logins", col_logins),
                ("mes", col_mes),
                ("año", col_anio),
            ]
            if col is None
        ]
        if missing_cols:
            st.warning(
                "Faltan columnas en el Excel de logins: " + ", ".join(missing_cols)
            )
            return None

        usage = usage_df.rename(
            columns={
                col_cliente: "cliente",
                col_logins: "logins",
                col_mes: "mes",
                col_anio: "anio",
            }
        ).copy()
        usage["cliente_original"] = usage["cliente"].astype(str)
        usage["cliente_display"] = usage["cliente_original"].map(TextNormalizer.remove_accents)
        usage["cliente_norm"] = usage["cliente_original"].map(TextNormalizer.normalize_column_name)
        usage["cliente"] = usage["cliente_display"]
        usage["anio"] = pd.to_numeric(usage["anio"], errors="coerce")
        usage["logins"] = pd.to_numeric(usage["logins"], errors="coerce").fillna(0)
        usage["Cliente"] = usage["cliente_display"]

        if selected_client:
            selected_clients_norm = {
                TextNormalizer.normalize_column_name(client)
                for client in selected_client
            }
            usage = usage[usage["cliente_norm"].isin(selected_clients_norm)]

        if usage.empty:
            st.info("No hay datos de logins para los filtros seleccionados.")
            return None

        month_map = {name.lower(): num for num, name in self.config.MONTH_NAMES_ES.items()}
        month_numeric = pd.to_numeric(usage["mes"], errors="coerce")
        if month_numeric.notna().any():
            usage["mes_num"] = month_numeric
        else:
            usage["mes_num"] = (
                usage["mes"].astype(str).str.strip().str.lower().map(month_map)
            )

        usage = usage.dropna(subset=["mes_num"])
        if usage.empty:
            st.info("No hay meses validos para los filtros seleccionados.")
            return None

        usage["mes_num"] = usage["mes_num"].astype(int)

        _, years = resolve_comparison_years(selected_year)

        tables = []
        for year in years:
            year_usage = usage[usage["anio"] == year]
            if year_usage.empty:
                st.info(f"ℹ️ No hay datos de logins para el año {year}")
                continue
            pivot = (
                year_usage.groupby(["cliente", "mes_num"])["logins"]
                .sum()
                .unstack(fill_value=0)
                .sort_index()
            )

            month_order = list(range(1, 13))
            pivot = pivot.reindex(columns=month_order, fill_value=0)
            pivot.columns = [self.config.MONTH_NAMES_ES.get(m, str(m)) for m in pivot.columns]
            pivot["Total"] = pivot.sum(axis=1)
            pivot = pivot.sort_values(by="Total", ascending=False)
            pivot.index.name = "Cliente"

            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            st.warning("No hay datos de logins para los filtros seleccionados.")
            return None

        combined_table = pd.concat(tables)
        combined_table.index.name = "Cliente"
        display_table = format_numeric_display_table(combined_table)
        render_table_in_details_expander(display_table, "Usabilidad")

        usage_chart = usage[usage["anio"].isin(years)].copy()
        if not usage_chart.empty:
            usage_fig = self.chart_renderer.render_usage_trend_chart(
                usage_chart,
                None,
                chart_key=build_widget_key("chart", "usage_activity"),
            )
            export_charts.append(("Usabilidad - Actividad", usage_fig))

        return display_table
