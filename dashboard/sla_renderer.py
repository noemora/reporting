"""Renderers for SLA-oriented KPI sections."""
from typing import Optional

import pandas as pd
import streamlit as st

from utils import (
    map_priority_sort,
    normalize_priority_labels,
)

from .presentation_helpers import (
    info_no_data_year,
    info_no_data_year_with_zeros,
    info_no_sla_data_year,
    info_no_valid_priorities_year,
    warning_no_data_section,
)
from .section_renderer_base import SectionRendererBase


class SlaSectionsRenderer(SectionRendererBase):
    """Render KPI sections related to SLA compliance."""

    def render_resolucion_section(
        self, base_filtered: pd.DataFrame, selected_year: Optional[int]
    ) -> Optional[pd.DataFrame]:
        st.subheader("KPI - Service Level Agreement (SLA)")
        current_year, years = self._year_window(selected_year)

        tables = []
        for year in years:
            sla_base = self.filter.filter_resolved_by_year(base_filtered, year)
            sla_prod = self.filter.filter_production_environment(sla_base)
            if sla_prod.empty:
                info_no_data_year(year)
                continue

            sla_prod = sla_prod.copy()
            sla_prod["Mes"] = pd.to_datetime(sla_prod["Hora de resolucion"], errors="coerce").dt.month
            sla_prod["Estado de resolucion"] = self._normalize_resolution_status_for_display(
                sla_prod["Estado de resolucion"]
            )

            pivot = self.table_builder.build_pivot_table(
                sla_prod, "Estado de resolucion", "Sin estado de resolución"
            )
            pivot = self.table_builder.add_sla_percentage_row(pivot)
            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            warning_no_data_section("KPI - SLA")
            return None

        combined_table = pd.concat(tables)
        combined_table.index.name = "Estado de resolucion"
        formatted_table = self._format_table(
            combined_table,
            coerce_numeric=False,
            replace_comma_with_dot=False,
        )
        self._render_table_in_details_expander(formatted_table, "SLA")

        chart_years = [current_year - 1, current_year]
        chart_df = base_filtered.copy()
        chart_df = chart_df[pd.to_datetime(chart_df["Hora de resolucion"], errors="coerce").dt.year.isin(chart_years)]
        chart_df = self.filter.filter_production_environment(chart_df)
        if not chart_df.empty:
            chart_df = chart_df.copy()
            chart_df["Periodo"] = (
                pd.to_datetime(chart_df["Hora de resolucion"], errors="coerce")
                .dt.to_period("M")
                .dt.to_timestamp()
            )
            chart_df["Estado de resolucion"] = self._normalize_resolution_status_for_display(
                chart_df["Estado de resolucion"]
            )
            sla_fig = self.chart_renderer.render_trend_chart(
                chart_df,
                "Estado de resolucion",
                None,
                chart_key=self._build_widget_key("chart", "sla"),
            )
            self._append_export_chart("Consulta e Incidencias - SLA", sla_fig)

        return formatted_table

    def render_sla_criticidad_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "sla_criticidad",
    ) -> Optional[pd.DataFrame]:
        st.subheader("KPI - SLA por Criticidad")
        current_year, years = self._year_window(selected_year)

        status_order_map = {"Incumplido": 0, "Cumplido": 1}
        expected_priorities = ["Urgente", "Alta", "Media", "Baja"]
        expected_labels = [
            f"{status} - {priority}"
            for status in ["Incumplido", "Cumplido"]
            for priority in expected_priorities
        ]

        def build_zero_pivot() -> pd.DataFrame:
            month_columns = [self.config.MONTH_NAMES_ES[m] for m in range(1, 13)]
            zero_pivot = pd.DataFrame(0, index=expected_labels, columns=month_columns)
            zero_pivot["Total"] = 0
            zero_pivot.index.name = "SLA Criticidad"
            return zero_pivot

        tables = []
        chart_frames = []
        for year in years:
            sla_base = self.filter.filter_resolved_by_year(base_filtered, year)
            sla_prod = self.filter.filter_production_environment(sla_base)
            if sla_prod.empty:
                info_no_data_year_with_zeros(year)
                pivot_body = build_zero_pivot()
                year_row = pd.DataFrame(
                    [{col: pd.NA for col in pivot_body.columns}],
                    index=[f"~~ AÑO {year} ~~"],
                )
                year_row.index.name = pivot_body.index.name
                tables.extend([year_row, pivot_body])
                continue

            sla_prod = sla_prod.copy()
            sla_prod["Estado de resolucion"] = self._normalize_resolution_status_for_display(
                sla_prod["Estado de resolucion"]
            )
            sla_prod["SLA Estado"] = sla_prod["Estado de resolucion"]
            sla_prod = sla_prod[sla_prod["SLA Estado"].isin(["Cumplido", "Incumplido"])]
            if sla_prod.empty:
                info_no_sla_data_year(year)
                pivot_body = build_zero_pivot()
                year_row = pd.DataFrame(
                    [{col: pd.NA for col in pivot_body.columns}],
                    index=[f"~~ AÑO {year} ~~"],
                )
                year_row.index.name = pivot_body.index.name
                tables.extend([year_row, pivot_body])
                continue

            sla_prod["Prioridad ES"] = normalize_priority_labels(sla_prod["Prioridad"])
            sla_prod = sla_prod[sla_prod["Prioridad ES"].ne("Sin criticidad")]
            if sla_prod.empty:
                info_no_valid_priorities_year(year)
                pivot_body = build_zero_pivot()
                year_row = pd.DataFrame(
                    [{col: pd.NA for col in pivot_body.columns}],
                    index=[f"~~ AÑO {year} ~~"],
                )
                year_row.index.name = pivot_body.index.name
                tables.extend([year_row, pivot_body])
                continue

            sla_prod["SLA Criticidad"] = (
                sla_prod["SLA Estado"].astype(str).str.strip()
                + " - "
                + sla_prod["Prioridad ES"].astype(str).str.strip()
            )
            sla_prod["Mes"] = pd.to_datetime(sla_prod["Hora de resolucion"], errors="coerce").dt.month

            pivot = self.table_builder.build_pivot_table(
                sla_prod, "SLA Criticidad", "Sin criticidad"
            )
            pivot_body = pivot.drop(index="Total") if "Total" in pivot.index else pivot

            pivot_body = pivot_body[
                ~pivot_body.index.to_series().astype(str).str.lower().str.contains("sin criticidad", na=False)
            ]

            missing_labels = [label for label in expected_labels if label not in pivot_body.index]
            if missing_labels:
                missing_rows = pd.DataFrame(0, index=missing_labels, columns=pivot_body.columns)
                pivot_body = pd.concat([pivot_body, missing_rows])

            labels = pivot_body.index.to_series().astype(str)
            status_part = labels.str.split(" - ").str[0].str.strip()
            priority_part = labels.str.split(" - ").str[1:].str.join(" - ").str.strip()
            status_sort = status_part.map(status_order_map).fillna(99)
            priority_sort = map_priority_sort(priority_part).fillna(99)
            tie_breaker = labels.str.strip().str.lower()
            pivot_body = pivot_body.assign(
                _status_sort=status_sort.values,
                _priority_sort=priority_sort.values,
                _tie=tie_breaker.values,
            )
            pivot_body = pivot_body.sort_values(
                by=["_status_sort", "_priority_sort", "_tie"]
            ).drop(columns=["_status_sort", "_priority_sort", "_tie"])

            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot_body.columns}],
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot_body.index.name
            tables.extend([year_row, pivot_body])
            chart_frames.append(sla_prod)

        if not tables:
            warning_no_data_section("KPI - SLA por Criticidad")
            return None

        combined_table = pd.concat(tables)
        combined_table.index.name = "SLA - Criticidad"
        display_table = self._format_table(combined_table)
        self._render_table_in_details_expander(display_table, "SLA por Criticidad")

        if chart_frames:
            chart_df = pd.concat(chart_frames, ignore_index=True)
            chart_df["Periodo"] = (
                pd.to_datetime(chart_df["Hora de resolucion"], errors="coerce")
                .dt.to_period("M")
                .dt.to_timestamp()
            )
            chart_labels = chart_df["SLA Criticidad"].astype(str).str.strip()
            chart_status = chart_labels.str.split(" - ").str[0].str.strip()
            chart_priority = chart_labels.str.split(" - ").str[1:].str.join(" - ").str.strip()
            chart_status_sort = chart_status.map(status_order_map).fillna(99)
            chart_priority_sort = map_priority_sort(chart_priority).fillna(99)
            chart_order = (
                pd.DataFrame(
                    {
                        "label": chart_labels,
                        "status_sort": chart_status_sort,
                        "priority_sort": chart_priority_sort,
                        "tie": chart_labels.str.lower(),
                    }
                )
                .drop_duplicates(subset=["label"])
                .sort_values(by=["status_sort", "priority_sort", "tie"])["label"]
                .tolist()
            )
            chart_fig = self.chart_renderer.render_trend_chart(
                chart_df,
                "SLA Criticidad",
                None,
                chart_key=self._build_widget_key("chart", chart_key_suffix),
                category_order=chart_order,
            )
            chart_label = export_chart_label or "KPI - SLA por Criticidad"
            self._append_export_chart(chart_label, chart_fig)

        return display_table
