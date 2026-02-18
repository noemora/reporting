"""Dashboard orchestration and coordination."""
from typing import List, Optional
import pandas as pd
import streamlit as st

from config import AppConfig
from data import DataFilter
from services import TableBuilder
from ui import ChartRenderer, UIRenderer
from utils import TextNormalizer


class DashboardOrchestrator:
    """Orchestrates the entire dashboard rendering process."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.filter = DataFilter(config)
        self.table_builder = TableBuilder(config)
        self.chart_renderer = ChartRenderer(config)
        self.ui_renderer = UIRenderer()
    
    def render_dashboard(self, df: pd.DataFrame, usage_df: Optional[pd.DataFrame] = None) -> None:
        """Render complete hybrid dashboard."""
        # Render filters
        st.subheader("Filtros")
        selected_year, selected_client, selected_team = self._render_filters(df)

        self._render_usage_table(usage_df, selected_year, selected_client)
        
        base_filtered = self.filter.filter_by_client(df, selected_client)
        base_filtered = self.filter.filter_by_team(base_filtered, selected_team)
        base_filtered = self.filter.filter_by_types(
            base_filtered, ["Consulta de informacion", "Incidencia"]
        )

        st.header("KPIs - Consulta de Informacion e Incidencias")
        st.subheader("Análisis de tickets en ambientes productivos")

        if base_filtered.empty:
            st.warning("No hay datos para Consulta de Informacion e Incidencias con los filtros seleccionados.")
        else:
            # Render missing fields
            # self.ui_renderer.render_missing_fields_expander(filtered_prod, filtered)

            # Render analysis sections
            self._render_incidents_table(base_filtered, selected_year)
            self._render_team_section(base_filtered, selected_year, prod_only=True)
            self._render_resolucion_section(base_filtered, selected_year)
            self._render_modulo_section(base_filtered, selected_year, prod_only=True)
            self._render_ambiente_section(base_filtered, selected_year)
            self._render_estado_section(base_filtered, selected_year, prod_only=True)

        cambio_base = self.filter.filter_by_client(df, selected_client)
        cambio_base = self.filter.filter_by_team(cambio_base, selected_team)
        cambio_base = self.filter.filter_by_types(cambio_base, ["Cambio"])

        st.header("KPIs - Solicitudes de Cambio")
        st.subheader("Análisis de tickets de TODOS los ambientes")

        if cambio_base.empty:
            st.warning("No hay datos para Solicitudes de Cambio con los filtros seleccionados.")
        else:
            self._render_team_section(cambio_base, selected_year, prod_only=False)
            self._render_modulo_section(cambio_base, selected_year, prod_only=False)
            self._render_estado_section(cambio_base, selected_year, prod_only=False)

        internos_base = self.filter.filter_by_client(df, selected_client)
        internos_base = self.filter.filter_by_team(internos_base, selected_team)
        internos_base = self.filter.filter_by_types(internos_base, ["Interno"])

        st.header("KPIs - Solicitudes de Mejoras Técnicas")
        st.subheader("Análisis de tickets de TODOS los ambientes")

        if internos_base.empty:
            st.warning("No hay datos para Solicitudes de Mejoras Técnicas con los filtros seleccionados.")
        else:
            self._render_team_section(internos_base, selected_year, prod_only=False)
            self._render_modulo_section(internos_base, selected_year, prod_only=False)
            self._render_estado_section(internos_base, selected_year, prod_only=False)
    
    def _render_filters(self, df: pd.DataFrame) -> tuple:
        """Render filter controls and return selections."""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            year_options = sorted(df["Año"].dropna().unique(), reverse=True)
            current_year = pd.Timestamp.today().year
            year_index = 0
            if year_options:
                year_index = min(
                    range(len(year_options)),
                    key=lambda idx: abs(year_options[idx] - current_year),
                )
            selected_year = (
                st.selectbox(
                    "Año",
                    year_options,
                    index=year_index,
                    key="hybrid_year",
                    format_func=lambda value: f"{int(value) - 1} - {int(value)}",
                )
                if year_options
                else None
            )
        
        with col2:
            client_options = sorted(df["Grupo"].dropna().unique())
            selected_client = (
                st.selectbox("Cliente (Grupo)", ["Todos"] + client_options, key="hybrid_cliente")
                if client_options
                else "Todos"
            )
        
        with col3:
            team_options = sorted(df["Team Asignado"].dropna().unique())
            selected_team = (
                st.multiselect("Team Asignado", team_options, default=[], key="hybrid_team")
                if team_options
                else []
            )
        
        return selected_year, selected_client, selected_team

    def _render_usage_table(
        self,
        usage_df: Optional[pd.DataFrame],
        selected_year: Optional[int],
        selected_client: str,
    ) -> None:
        """Render the platform usage table from the logins Excel."""
        st.header("Usabilidad - Actividad en la plataforma")
        if usage_df is None or usage_df.empty:
            st.info("No hay datos de logins para mostrar.")
            return

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
            return

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

        if selected_client and selected_client != "Todos":
            selected_client_norm = TextNormalizer.normalize_column_name(selected_client)
            usage = usage[usage["cliente_norm"] == selected_client_norm]

        if usage.empty:
            st.info("No hay datos de logins para los filtros seleccionados.")
            return

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
            return

        usage["mes_num"] = usage["mes_num"].astype(int)

        current_year = selected_year or pd.Timestamp.today().year
        years = [current_year - 1, current_year]

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
                index=[f"AÑO {year}"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            st.warning("No hay datos de logins para los filtros seleccionados.")
            return

        combined_table = pd.concat(tables)
        combined_table.index.name = "Cliente"
        numeric_cols = [col for col in combined_table.columns]
        combined_table[numeric_cols] = combined_table[numeric_cols].apply(
            pd.to_numeric, errors="coerce"
        )
        display_table = combined_table.apply(
            lambda col: col.map(
                lambda value: ""
                if pd.isna(value)
                else f"{value:,.0f}".replace(",", ".")
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                else str(value)
            )
        )
        st.table(display_table)

        usage_chart = usage[usage["anio"].isin(years)].copy()
        if not usage_chart.empty:
            self.chart_renderer.render_usage_trend_chart(usage_chart, None)
    
    def _apply_type_filters(
        self,
        df: pd.DataFrame,
        selected_client: str,
        selected_year: Optional[int],
        selected_team: List[str],
        types: List[str],
    ) -> pd.DataFrame:
        """Apply client, year, team, and ticket type filters."""
        filtered = self.filter.filter_by_client(df, selected_client)
        filtered = self.filter.filter_by_year(filtered, selected_year)
        filtered = self.filter.filter_by_team(filtered, selected_team)
        filtered = self.filter.filter_by_types(filtered, types)
        return filtered
    
    def _render_incidents_table(
        self, base_filtered: pd.DataFrame, selected_year: Optional[int]
    ) -> None:
        """Render the incidents and consultation table."""
        st.subheader("KPI - Flujo de tickets")
        current_year = selected_year or pd.Timestamp.today().year
        years = [current_year - 1, current_year]

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
            resolved_mask = (
                resolved_prod["Estado de resolucion"].astype(str).str.lower().isin(self.config.RESOLVED_STATES)
                | resolved_prod["Estado"].astype(str).str.lower().isin(self.config.RESOLVED_STATES)
            )
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
                st.info(f"ℹ️ No hay datos para el año {year}")
                continue

            table = self.table_builder.build_monthly_counts_table(created_counts, resolved_counts)
            year_row = pd.DataFrame(
                [{col: pd.NA for col in table.columns}],
                index=[f"AÑO {year}"],
            )
            tables.extend([year_row, table])

        if not tables:
            st.warning("No hay datos para Flujo de tickets con los filtros seleccionados.")
            return

        combined_table = pd.concat(tables)
        combined_table.index.name = "Tickets"
        combined_table[combined_table.columns] = combined_table[combined_table.columns].apply(
            pd.to_numeric, errors="coerce"
        )
        display_table = combined_table.apply(
            lambda col: col.map(
                lambda value: ""
                if pd.isna(value)
                else f"{value:,.0f}".replace(",", ".")
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                else str(value)
            )
        )
        st.table(display_table)

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

            resolved_mask = (
                chart_df["Estado de resolucion"].astype(str).str.lower().isin(self.config.RESOLVED_STATES)
                | chart_df["Estado"].astype(str).str.lower().isin(self.config.RESOLVED_STATES)
            )
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
                            "Tipo": "Creados por cliente",
                            "Tickets": created_counts.values,
                        }
                    ),
                    pd.DataFrame(
                        {
                            "Periodo": all_months,
                            "Tipo": "Resueltos por Soporte N5",
                            "Tickets": resolved_counts.values,
                        }
                    ),
                ],
                ignore_index=True,
            )
            self.chart_renderer.render_flow_chart(flow_chart)
    
    def _render_team_section(
        self, base_filtered: pd.DataFrame, selected_year: Optional[int], prod_only: bool
    ) -> None:
        """Render team asignado analysis section."""
        st.subheader("KPI - Team Asignado")
        current_year = selected_year or pd.Timestamp.today().year
        years = [current_year - 1, current_year]

        tables = []
        for year in years:
            year_df = self.filter.filter_by_year(base_filtered, year)
            if prod_only:
                year_df = self.filter.filter_production_environment(year_df)
            if year_df.empty:
                st.info(f"ℹ️ No hay datos para el año {year}")
                continue
            pivot = self.table_builder.build_pivot_table(
                year_df, "Team Asignado", "Sin team asignado"
            )
            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"AÑO {year}"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            st.warning("No hay datos para KPI - Team Asignado con los filtros seleccionados.")
            return

        combined_table = pd.concat(tables)
        combined_table.index.name = "Team Asignado"
        combined_table[combined_table.columns] = combined_table[combined_table.columns].apply(
            pd.to_numeric, errors="coerce"
        )
        display_table = combined_table.apply(
            lambda col: col.map(
                lambda value: ""
                if pd.isna(value)
                else f"{value:,.0f}".replace(",", ".")
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                else str(value)
            )
        )
        st.table(display_table)

        chart_years = [current_year - 1, current_year]
        chart_df = base_filtered[base_filtered["Año"].isin(chart_years)].copy()
        if prod_only:
            chart_df = self.filter.filter_production_environment(chart_df)
        if not chart_df.empty:
            self.chart_renderer.render_trend_chart(
                chart_df, "Team Asignado", None
            )

    def _render_estado_section(
        self, base_filtered: pd.DataFrame, selected_year: Optional[int], prod_only: bool
    ) -> None:
        """Render estado (status) analysis section."""
        st.subheader("KPI - Estado")
        current_year = selected_year or pd.Timestamp.today().year
        years = [current_year - 1, current_year]

        tables = []
        for year in years:
            year_df = self.filter.filter_by_year(base_filtered, year)
            if prod_only:
                year_df = self.filter.filter_production_environment(year_df)
            if year_df.empty:
                st.info(f"ℹ️ No hay datos para el año {year}")
                continue
            pivot = self.table_builder.build_pivot_table(year_df, "Estado", "Sin estado")
            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"AÑO {year}"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            st.warning("No hay datos para KPI - Estado con los filtros seleccionados.")
            return

        combined_table = pd.concat(tables)
        combined_table.index.name = "Estado"
        combined_table[combined_table.columns] = combined_table[combined_table.columns].apply(
            pd.to_numeric, errors="coerce"
        )
        display_table = combined_table.apply(
            lambda col: col.map(
                lambda value: ""
                if pd.isna(value)
                else f"{value:,.0f}".replace(",", ".")
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                else str(value)
            )
        )
        st.table(display_table)

        chart_years = [current_year - 1, current_year]
        chart_df = base_filtered[base_filtered["Año"].isin(chart_years)].copy()
        if prod_only:
            chart_df = self.filter.filter_production_environment(chart_df)
        if not chart_df.empty:
            self.chart_renderer.render_trend_chart(chart_df, "Estado", None)

    def _render_modulo_section(
        self, base_filtered: pd.DataFrame, selected_year: Optional[int], prod_only: bool
    ) -> None:
        """Render modulo (module) analysis section."""
        st.subheader("KPI - Módulo")
        current_year = selected_year or pd.Timestamp.today().year
        years = [current_year - 1, current_year]

        tables = []
        for year in years:
            year_df = self.filter.filter_by_year(base_filtered, year)
            if prod_only:
                year_df = self.filter.filter_production_environment(year_df)
            if year_df.empty:
                st.info(f"ℹ️ No hay datos para el año {year}")
                continue
            pivot = self.table_builder.build_pivot_table(year_df, "Modulo", "Sin módulo")
            if "Total" in pivot.index:
                total_row = pivot.loc[["Total"]]
                pivot = pivot.drop(index="Total").sort_values(by="Total", ascending=False)
                pivot = pd.concat([pivot, total_row])
            else:
                pivot = pivot.sort_values(by="Total", ascending=False)
            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"AÑO {year}"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            st.warning("No hay datos para KPI - Módulo con los filtros seleccionados.")
            return

        combined_table = pd.concat(tables)
        combined_table.index.name = "Modulo"
        combined_table[combined_table.columns] = combined_table[combined_table.columns].apply(
            pd.to_numeric, errors="coerce"
        )
        display_table = combined_table.apply(
            lambda col: col.map(
                lambda value: ""
                if pd.isna(value)
                else f"{value:,.0f}".replace(",", ".")
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                else str(value)
            )
        )
        st.table(display_table)

    def _render_ambiente_section(
        self, base_filtered: pd.DataFrame, selected_year: Optional[int]
    ) -> None:
        """Render ambiente (environment) analysis section."""
        st.subheader("KPI - Ambiente")
        current_year = selected_year or pd.Timestamp.today().year
        years = [current_year - 1, current_year]

        tables = []
        for year in years:
            year_df = self.filter.filter_by_year(base_filtered, year)
            if year_df.empty:
                st.info(f"ℹ️ No hay datos para el año {year}")
                continue
            pivot = self.table_builder.build_pivot_table(
                year_df, "Ambiente", "Sin ambiente"
            )
            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"AÑO {year}"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            st.warning("No hay datos para KPI - Ambiente con los filtros seleccionados.")
            return

        combined_table = pd.concat(tables)
        combined_table.index.name = "Ambiente"
        combined_table[combined_table.columns] = combined_table[combined_table.columns].apply(
            pd.to_numeric, errors="coerce"
        )
        display_table = combined_table.apply(
            lambda col: col.map(
                lambda value: ""
                if pd.isna(value)
                else f"{value:,.0f}".replace(",", ".")
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                else str(value)
            )
        )
        st.table(display_table)

        chart_years = [current_year - 1, current_year]
        chart_df = base_filtered[base_filtered["Año"].isin(chart_years)].copy()
        if not chart_df.empty:
            self.chart_renderer.render_trend_chart(chart_df, "Ambiente", None)

    def _render_resolucion_section(
        self, base_filtered: pd.DataFrame, selected_year: Optional[int]
    ) -> None:
        """Render resolucion (resolution) analysis section."""
        st.subheader("KPI - Service Level Agreement (SLA)")
        current_year = selected_year or pd.Timestamp.today().year
        years = [current_year - 1, current_year]

        tables = []
        for year in years:
            sla_base = self.filter.filter_resolved_by_year(base_filtered, year)
            sla_prod = self.filter.filter_production_environment(sla_base)
            if sla_prod.empty:
                st.info(f"ℹ️ No hay datos para el año {year}")
                continue

            sla_prod = sla_prod.copy()
            sla_prod["Mes"] = pd.to_datetime(sla_prod["Hora de resolucion"], errors="coerce").dt.month

            pivot = self.table_builder.build_pivot_table(
                sla_prod, "Estado de resolucion", "Sin estado de resolución"
            )
            pivot = pivot.rename(
                index={
                    label: "Cumplido"
                    for label in pivot.index
                    if str(label).strip().lower() == "within sla"
                }
            )
            pivot = pivot.rename(
                index={
                    label: "Incumplido"
                    for label in pivot.index
                    if str(label).strip().lower() == "sla violated"
                }
            )
            pivot = self.table_builder.add_sla_percentage_row(pivot)
            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"AÑO {year}"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            st.warning("No hay datos para KPI - SLA con los filtros seleccionados.")
            return

        combined_table = pd.concat(tables)
        combined_table.index.name = "Estado de resolucion"
        formatted_table = combined_table.apply(
            lambda col: col.map(
                lambda value: ""
                if pd.isna(value)
                else f"{value:,.0f}"
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                else str(value)
            )
        )
        st.table(formatted_table)

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
            self.chart_renderer.render_trend_chart(
                chart_df, "Estado de resolucion", None
            )
