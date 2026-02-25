"""Renderers for distribution-oriented KPI sections."""
from typing import List, Optional

import pandas as pd
import streamlit as st

from utils import (
    build_priority_category_order,
    map_priority_sort,
    normalize_priority_labels,
)

from .presentation_helpers import (
    info_no_data_year,
    info_no_top_modules_year,
    warning_no_data_section,
)
from .section_renderer_base import SectionRendererBase


class DistributionSectionsRenderer(SectionRendererBase):
    """Render KPI sections for flow and category distributions."""

    def render_incidents_table(
        self, base_filtered: pd.DataFrame, selected_year: Optional[int]
    ) -> Optional[pd.DataFrame]:
        st.subheader("KPI - Flujo de tickets")
        current_year, years = self._year_window(selected_year)

        tables = []
        for year in years:
            created_base = self.filter.filter_by_year(base_filtered, year)
            created_prod = self.filter.filter_production_environment(created_base)
            created_prod = created_prod.dropna(subset=["Hora de creacion"])
            month_order = list(range(1, 13))
            if created_prod.empty:
                created_counts = pd.Series(0, index=month_order)
            else:
                created_counts = (
                    created_prod.groupby(created_prod["Hora de creacion"].dt.month)["ID del ticket"]
                    .nunique()
                    .reindex(month_order, fill_value=0)
                )

            resolved_base = self.filter.filter_resolved_by_year(base_filtered, year)
            resolved_prod = self.filter.filter_production_environment(resolved_base)
            resolved_mask = self._build_resolved_mask(resolved_prod)
            if resolved_prod.empty:
                resolved_counts = pd.Series(0, index=month_order)
            else:
                resolved_counts = (
                    resolved_prod[resolved_mask]
                    .groupby(pd.to_datetime(resolved_prod["Hora de resolucion"], errors="coerce").dt.month)[
                        "ID del ticket"
                    ]
                    .nunique()
                    .reindex(month_order, fill_value=0)
                )

            if created_counts.sum() == 0 and resolved_counts.sum() == 0:
                info_no_data_year(year)
                continue

            table = self.table_builder.build_monthly_counts_table(created_counts, resolved_counts)
            year_row = pd.DataFrame(
                [{col: pd.NA for col in table.columns}],
                index=[f"~~ AÑO {year} ~~"],
            )
            tables.extend([year_row, table])

        if not tables:
            warning_no_data_section("Flujo de tickets")
            return None

        combined_table = pd.concat(tables)
        combined_table.index.name = "Tickets"
        display_table = self._format_table(combined_table)
        self._render_table_in_details_expander(display_table, "Flujo de tickets")

        chart_years = [current_year - 1, current_year]
        chart_df = base_filtered[base_filtered["Año"].isin(chart_years)].copy()
        chart_df = self.filter.filter_production_environment(chart_df)
        if not chart_df.empty:
            today = pd.Timestamp.today()
            all_months = []
            for year in chart_years:
                end_month = 12 if year != today.year else today.month
                all_months.extend(
                    pd.date_range(
                        start=f"{int(year)}-01-01",
                        end=f"{int(year)}-{int(end_month):02d}-01",
                        freq="MS",
                    )
                )
            all_months = pd.to_datetime(all_months)

            created_base = chart_df.dropna(subset=["Hora de creacion"]).copy()
            created_base["Periodo"] = (
                created_base["Hora de creacion"].dt.to_period("M").dt.to_timestamp()
            )
            created_counts = (
                created_base.groupby("Periodo")["ID del ticket"].nunique()
                .reindex(all_months, fill_value=0)
            )

            resolved_mask = self._build_resolved_mask(chart_df)
            resolved_base = chart_df[resolved_mask].copy()
            resolved_base["Periodo"] = (
                pd.to_datetime(resolved_base["Hora de resolucion"], errors="coerce")
                .dt.to_period("M")
                .dt.to_timestamp()
            )
            resolved_counts = (
                resolved_base.groupby("Periodo")["ID del ticket"].nunique()
                .reindex(all_months, fill_value=0)
            )

            flow_chart = pd.concat(
                [
                    pd.DataFrame(
                        {
                            "Periodo": all_months,
                            "Tipo": "Creados",
                            "Tickets": created_counts.values,
                        }
                    ),
                    pd.DataFrame(
                        {
                            "Periodo": all_months,
                            "Tipo": "Resueltos",
                            "Tickets": resolved_counts.values,
                        }
                    ),
                ],
                ignore_index=True,
            )
            flow_fig = self.chart_renderer.render_flow_chart(
                flow_chart,
                chart_key=self._build_widget_key("chart", "incidents_flow"),
            )
            self._append_export_chart("Consulta e Incidencias - Flujo", flow_fig)

        return display_table

    def render_team_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "team",
    ) -> Optional[pd.DataFrame]:
        st.subheader("KPI - Team Asignado")
        current_year, years = self._year_window(selected_year)

        tables = []
        for year in years:
            year_df = self.filter.filter_by_year(base_filtered, year)
            if prod_only:
                year_df = self.filter.filter_production_environment(year_df)
            if year_df.empty:
                info_no_data_year(year)
                continue
            pivot = self.table_builder.build_pivot_table(
                year_df, "Team Asignado", "Sin team asignado"
            )
            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            warning_no_data_section("KPI - Team Asignado")
            return None

        combined_table = pd.concat(tables)
        combined_table.index.name = "Team Asignado"
        display_table = self._format_table(combined_table)
        self._render_table_in_details_expander(display_table, "Team Asignado")

        chart_years = [current_year - 1, current_year]
        chart_df = base_filtered[base_filtered["Año"].isin(chart_years)].copy()
        if prod_only:
            chart_df = self.filter.filter_production_environment(chart_df)
        if not chart_df.empty:
            team_fig = self.chart_renderer.render_trend_chart(
                chart_df,
                "Team Asignado",
                None,
                chart_key=self._build_widget_key("chart", chart_key_suffix),
            )
            chart_label = export_chart_label or "KPI - Team Asignado"
            self._append_export_chart(chart_label, team_fig)

        return display_table

    def render_cliente_mensual_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "cliente_mensual",
    ) -> Optional[pd.DataFrame]:
        st.subheader("KPI - Cliente")
        current_year, years = self._year_window(selected_year)

        tables = []
        for year in years:
            year_df = self.filter.filter_by_year(base_filtered, year)
            if prod_only:
                year_df = self.filter.filter_production_environment(year_df)
            if year_df.empty:
                info_no_data_year(year)
                continue
            pivot = self.table_builder.build_pivot_table(
                year_df,
                "Grupo",
                "Sin cliente",
            )
            if "Total" in pivot.index:
                total_row = pivot.loc[["Total"]]
                pivot_body = pivot.drop(index="Total")
                pivot_body = pivot_body.sort_values(by="Total", ascending=False)
                pivot = pd.concat([pivot_body, total_row])
            else:
                pivot = pivot.sort_values(by="Total", ascending=False)

            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            warning_no_data_section("KPI - Cliente")
            return None

        combined_table = pd.concat(tables)
        combined_table.index.name = "Cliente"
        display_table = self._format_table(combined_table)
        self._render_table_in_details_expander(display_table, "KPI - Cliente")

        chart_years = [current_year - 1, current_year]
        chart_df = base_filtered[base_filtered["Año"].isin(chart_years)].copy()
        if prod_only:
            chart_df = self.filter.filter_production_environment(chart_df)
        if not chart_df.empty:
            cliente_fig = self.chart_renderer.render_trend_chart(
                chart_df,
                "Grupo",
                None,
                chart_key=self._build_widget_key("chart", chart_key_suffix),
            )
            chart_label = export_chart_label or "KPI - Cliente"
            self._append_export_chart(chart_label, cliente_fig)

        return display_table

    def render_criticidad_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "criticidad",
    ) -> Optional[pd.DataFrame]:
        st.subheader("KPI - Criticidad")
        current_year, years = self._year_window(selected_year)

        tables = []
        for year in years:
            year_df = self.filter.filter_by_year(base_filtered, year)
            if prod_only:
                year_df = self.filter.filter_production_environment(year_df)
            if year_df.empty:
                info_no_data_year(year)
                continue

            year_df = year_df.copy()
            year_df["Prioridad"] = normalize_priority_labels(year_df["Prioridad"])

            pivot = self.table_builder.build_pivot_table(
                year_df, "Prioridad", "Sin criticidad"
            )
            if "Total" in pivot.index:
                total_row = pivot.loc[["Total"]]
                pivot_body = pivot.drop(index="Total")
            else:
                total_row = None
                pivot_body = pivot

            priority_labels = pivot_body.index.to_series().astype(str)
            priority_sort = map_priority_sort(priority_labels)
            tie_breaker = priority_labels.str.strip().str.lower()
            pivot_body = pivot_body.assign(_prio_sort=priority_sort.values, _prio_tie=tie_breaker.values)
            pivot_body = pivot_body.sort_values(by=["_prio_sort", "_prio_tie"]).drop(columns=["_prio_sort", "_prio_tie"])

            pivot = pd.concat([pivot_body, total_row]) if total_row is not None else pivot_body

            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            warning_no_data_section("KPI - Criticidad")
            return None

        combined_table = pd.concat(tables)
        combined_table.index.name = "Prioridad"
        display_table = self._format_table(combined_table)
        self._render_table_in_details_expander(display_table, "Criticidad")

        chart_years = [current_year - 1, current_year]
        chart_df = base_filtered[base_filtered["Año"].isin(chart_years)].copy()
        if prod_only:
            chart_df = self.filter.filter_production_environment(chart_df)
        if not chart_df.empty:
            chart_df = chart_df.copy()
            chart_df["Prioridad"] = normalize_priority_labels(chart_df["Prioridad"])
            chart_priority_order = build_priority_category_order(chart_df["Prioridad"])
            criticidad_fig = self.chart_renderer.render_trend_chart(
                chart_df,
                "Prioridad",
                None,
                chart_key=self._build_widget_key("chart", chart_key_suffix),
                category_order=chart_priority_order,
            )
            chart_label = export_chart_label or "KPI - Criticidad"
            self._append_export_chart(chart_label, criticidad_fig)

        return display_table

    def render_modulo_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "modulo",
    ) -> Optional[pd.DataFrame]:
        st.subheader("KPI - Módulo")
        _, years = self._year_window(selected_year)
        show_all_modules = st.toggle(
            "Mostrar todos los módulos",
            value=False,
            key=self._build_widget_key("toggle", chart_key_suffix, "all_modulos"),
            help="Por defecto se muestra TOP 5 por total de casos.",
        )

        ranking_df = base_filtered[base_filtered["Año"].isin(years)].copy()
        if prod_only:
            ranking_df = self.filter.filter_production_environment(ranking_df)

        top_modules: Optional[List[str]] = None
        if not show_all_modules and not ranking_df.empty:
            ranking_df = ranking_df.copy()
            ranking_df["Modulo"] = ranking_df["Modulo"].fillna("Sin módulo")
            top_modules = (
                ranking_df.groupby("Modulo")["ID del ticket"]
                .nunique()
                .sort_values(ascending=False)
                .head(5)
                .index.tolist()
            )
            if top_modules:
                st.caption("Mostrando TOP 5 módulos por total de casos.")

        tables = []
        for year in years:
            year_df = self.filter.filter_by_year(base_filtered, year)
            if prod_only:
                year_df = self.filter.filter_production_environment(year_df)
            if year_df.empty:
                info_no_data_year(year)
                continue
            pivot = self.table_builder.build_pivot_table(year_df, "Modulo", "Sin módulo")

            if top_modules:
                available_modules = [module for module in top_modules if module in pivot.index]
                pivot = pivot.loc[available_modules]
                if pivot.empty:
                    info_no_top_modules_year(year)
                    continue

            if "Total" in pivot.index:
                total_row = pivot.loc[["Total"]]
                pivot = pivot.drop(index="Total").sort_values(by="Total", ascending=False)
                pivot = pd.concat([pivot, total_row])
            else:
                pivot = pivot.sort_values(by="Total", ascending=False)
            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            warning_no_data_section("KPI - Módulo")
            return None

        combined_table = pd.concat(tables)
        combined_table.index.name = "Modulo"
        display_table = self._format_table(combined_table)
        self._render_table_in_details_expander(display_table, "Módulo")

        if not show_all_modules:
            chart_df = base_filtered[base_filtered["Año"].isin(years)].copy()
            if prod_only:
                chart_df = self.filter.filter_production_environment(chart_df)
            if top_modules:
                chart_df = chart_df.copy()
                chart_df["Modulo"] = chart_df["Modulo"].fillna("Sin módulo")
                chart_df = chart_df[chart_df["Modulo"].isin(top_modules)]

            if not chart_df.empty:
                modulo_fig = self.chart_renderer.render_trend_chart(
                    chart_df,
                    "Modulo",
                    None,
                    chart_key=self._build_widget_key("chart", chart_key_suffix),
                    category_order=top_modules,
                )
                chart_label = export_chart_label or "KPI - Módulo"
                self._append_export_chart(chart_label, modulo_fig)

        return display_table

    def render_ambiente_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        export_chart_label: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        st.subheader("KPI - Ambiente")
        current_year, years = self._year_window(selected_year)

        tables = []
        for year in years:
            year_df = self.filter.filter_by_year(base_filtered, year)
            if year_df.empty:
                info_no_data_year(year)
                continue
            pivot = self.table_builder.build_pivot_table(
                year_df, "Ambiente", "Sin ambiente"
            )
            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            warning_no_data_section("KPI - Ambiente")
            return None

        combined_table = pd.concat(tables)
        combined_table.index.name = "Ambiente"
        display_table = self._format_table(combined_table)
        self._render_table_in_details_expander(display_table, "Ambiente")

        chart_years = [current_year - 1, current_year]
        chart_df = base_filtered[base_filtered["Año"].isin(chart_years)].copy()
        if not chart_df.empty:
            ambiente_fig = self.chart_renderer.render_trend_chart(
                chart_df,
                "Ambiente",
                None,
                chart_key=self._build_widget_key("chart", "ambiente"),
            )
            chart_label = export_chart_label or "KPI - Ambiente"
            self._append_export_chart(chart_label, ambiente_fig)

        return display_table
