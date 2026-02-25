"""Renderers for status-oriented KPI sections."""
from typing import Optional

import pandas as pd
import streamlit as st

from utils import COMMERCIAL_STATUS_ORDER, build_commercial_estado

from .presentation_helpers import info_no_data_year, warning_no_data_section
from .section_renderer_base import SectionRendererBase


class StatusSectionsRenderer(SectionRendererBase):
    """Render KPI sections related to ticket status."""

    def render_estado_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "estado",
        commercial_mode: bool = False,
        show_unresolved_ticket_ids: bool = False,
    ) -> Optional[pd.DataFrame]:
        st.subheader("KPI - Estado")
        current_year, years = self._year_window(selected_year)

        tables = []
        for year in years:
            year_df = self.filter.filter_by_year(base_filtered, year)
            if prod_only:
                year_df = self.filter.filter_production_environment(year_df)
            if year_df.empty:
                info_no_data_year(year)
                continue

            year_df = self._build_estado_grouped(year_df, "Estado Agrupado")

            if commercial_mode:
                estado_df = year_df.copy()
                estado_df["Estado Comercial"] = build_commercial_estado(estado_df["Estado Agrupado"])
                estado_df = estado_df.dropna(subset=["Estado Comercial"])

                month_order = list(range(1, 13))
                if estado_df.empty:
                    pivot = pd.DataFrame(0, index=COMMERCIAL_STATUS_ORDER, columns=month_order)
                else:
                    pivot = (
                        estado_df.pivot_table(
                            index="Estado Comercial",
                            columns="Mes",
                            values="ID del ticket",
                            aggfunc="nunique",
                            fill_value=0,
                        )
                        .reindex(index=COMMERCIAL_STATUS_ORDER, fill_value=0)
                        .reindex(columns=month_order, fill_value=0)
                    )
                pivot.columns = [self.config.MONTH_NAMES_ES.get(m, str(m)) for m in pivot.columns]
                pivot["Total"] = pivot.sum(axis=1)
                pivot.loc["Total"] = pivot.sum(axis=0)
            else:
                pivot = self.table_builder.build_pivot_table(year_df, "Estado Agrupado", "Sin estado")

            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            warning_no_data_section("KPI - Estado")
            return None

        combined_table = pd.concat(tables)
        combined_table.index.name = "Estado"
        display_table = self._format_table(combined_table)
        self._render_table_in_details_expander(display_table, "Estado")

        if show_unresolved_ticket_ids:
            detail_df = base_filtered[base_filtered["Año"].isin(years)].copy()
            if prod_only:
                detail_df = self.filter.filter_production_environment(detail_df)

            with st.expander("Detalle de tickets no resueltos", expanded=False):
                if detail_df.empty:
                    st.info("No hay tickets para evaluar con los filtros seleccionados.")
                else:
                    unresolved_mask = ~self._build_resolved_mask(detail_df)
                    unresolved_detail = detail_df.loc[
                        unresolved_mask,
                        ["ID del ticket", "Hora de creacion", "Mes", "Año"],
                    ].copy()
                    unresolved_detail["ID del ticket"] = (
                        unresolved_detail["ID del ticket"].astype(str).str.strip()
                    )
                    unresolved_detail = unresolved_detail[
                        unresolved_detail["ID del ticket"].ne("")
                    ].drop_duplicates(subset=["ID del ticket"])

                    month_from_creation = pd.to_datetime(
                        unresolved_detail["Hora de creacion"], errors="coerce"
                    ).dt.month
                    month_fallback = pd.to_numeric(unresolved_detail["Mes"], errors="coerce")
                    unresolved_detail["Mes Num"] = month_from_creation.fillna(month_fallback)
                    unresolved_detail["Mes Num"] = (
                        pd.to_numeric(unresolved_detail["Mes Num"], errors="coerce")
                        .fillna(0)
                        .astype(int)
                    )
                    unresolved_detail["Mes"] = unresolved_detail["Mes Num"].map(
                        lambda month: self.config.MONTH_NAMES_ES.get(month, "Sin mes")
                    )
                    unresolved_detail["Año Ref"] = pd.to_datetime(
                        unresolved_detail["Hora de creacion"], errors="coerce"
                    ).dt.year
                    unresolved_detail["Año Ref"] = (
                        unresolved_detail["Año Ref"]
                        .fillna(pd.to_numeric(unresolved_detail["Año"], errors="coerce"))
                        .fillna(0)
                        .astype(int)
                    )

                    unresolved_detail = unresolved_detail.sort_values(
                        by=["Año Ref", "Mes Num", "ID del ticket"],
                        ascending=[False, True, True],
                    )

                    if unresolved_detail.empty:
                        st.info("No hay tickets no resueltos con los filtros seleccionados.")
                    else:
                        grouped_detail = (
                            unresolved_detail.groupby(["Año Ref", "Mes Num", "Mes"], as_index=False)
                            .agg(casos=("ID del ticket", lambda values: sorted(pd.unique(values).tolist())))
                        )
                        grouped_detail["total"] = grouped_detail["casos"].map(len)

                        unresolved_payload = [
                            {
                                "anio": int(row["Año Ref"]),
                                "mes": row["Mes"],
                                "casos": row["casos"],
                                "total": int(row["total"]),
                            }
                            for _, row in grouped_detail.sort_values(
                                by=["Año Ref", "Mes Num"],
                                ascending=[False, True],
                            ).iterrows()
                        ]

                        st.caption(
                            f"Total de tickets no resueltos: {len(unresolved_detail['ID del ticket'])}"
                        )
                        st.json(unresolved_payload)

        chart_years = [current_year - 1, current_year]
        chart_df = base_filtered[base_filtered["Año"].isin(chart_years)].copy()
        if prod_only:
            chart_df = self.filter.filter_production_environment(chart_df)
        if not chart_df.empty:
            chart_df = self._build_estado_grouped(chart_df, "Estado Agrupado")
            category_order = None
            category_col = "Estado Agrupado"
            if commercial_mode:
                chart_df = chart_df.copy()
                chart_df["Estado Comercial"] = build_commercial_estado(chart_df["Estado Agrupado"])
                chart_df = chart_df.dropna(subset=["Estado Comercial"])
                category_col = "Estado Comercial"
                category_order = COMMERCIAL_STATUS_ORDER

            estado_fig = self.chart_renderer.render_trend_chart(
                chart_df,
                category_col,
                None,
                chart_key=self._build_widget_key("chart", chart_key_suffix),
                category_order=category_order,
            )
            chart_label = export_chart_label or "KPI - Estado"
            self._append_export_chart(chart_label, estado_fig)

        return display_table
