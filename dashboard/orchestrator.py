"""Dashboard orchestration and coordination."""
from typing import List, Optional, Set, Tuple
import pandas as pd
import streamlit as st

from config import AppConfig
from data import DataFilter
from services import ExportBuilder, TableBuilder
from ui import ChartRenderer, UIRenderer
from utils import TextNormalizer


class DashboardOrchestrator:
    """Orchestrates the entire dashboard rendering process."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.filter = DataFilter(config)
        self.table_builder = TableBuilder(config)
        self.export_builder = ExportBuilder()
        self.chart_renderer = ChartRenderer(config)
        self.ui_renderer = UIRenderer()

    @staticmethod
    def _render_table_in_details_expander(table: pd.DataFrame, section_label: str) -> None:
        """Render a table inside a details expander."""
        with st.expander(f"Ver detalles - {section_label}", expanded=False):
            st.table(table)

    def _normalized_resolved_states(self) -> Set[str]:
        """Return normalized resolved states from config."""
        return {
            str(state).strip().lower()
            for state in self.config.RESOLVED_STATES
            if str(state).strip()
        }

    def _build_estado_grouped(self, df: pd.DataFrame, target_col: str) -> pd.DataFrame:
        """Group all configured resolved states into 'Resuelto'."""
        grouped_df = df.copy()
        if "Estado" not in grouped_df.columns:
            grouped_df[target_col] = pd.NA
            return grouped_df

        estado_series = grouped_df["Estado"].astype("string").str.strip()
        estado_norm = estado_series.str.lower()
        estado_grouped = estado_series.mask(
            estado_norm.isin(self._normalized_resolved_states()),
            "Resuelto",
        )
        estado_grouped = estado_grouped.mask(estado_grouped.isna() | estado_grouped.eq(""), pd.NA)
        grouped_df[target_col] = estado_grouped
        return grouped_df

    def _build_resolved_mask(self, df: pd.DataFrame) -> pd.Series:
        """Build resolved mask using grouped Estado and Estado de resolucion."""
        resolved_states = self._normalized_resolved_states()
        grouped_df = self._build_estado_grouped(df, "Estado Agrupado")
        resolved_estado = grouped_df["Estado Agrupado"].astype(str).str.strip().str.lower().eq("resuelto")
        resolved_estado_resolucion = grouped_df["Estado de resolucion"].astype(str).str.strip().str.lower().isin(
            resolved_states
        )
        return resolved_estado | resolved_estado_resolucion

    def _build_widget_key(self, *parts: str) -> str:
        """Build a stable and unique Streamlit key for the active dashboard context."""
        normalized_parts = [
            str(part).strip().lower().replace(" ", "_").replace("-", "_")
            for part in parts
            if str(part).strip()
        ]
        if not normalized_parts:
            return self._widget_prefix
        return "_".join([self._widget_prefix, *normalized_parts])
    
    def render_dashboard(
        self,
        df: pd.DataFrame,
        usage_df: Optional[pd.DataFrame] = None,
        dashboard_name: str = "Dashboard Soporte",
        widget_prefix: str = "soporte",
    ) -> None:
        """Render dashboard according to selected dashboard type."""
        self._export_charts: List[Tuple[str, object]] = []
        self._widget_prefix = widget_prefix
        is_commercial_dashboard = str(widget_prefix).strip().lower() == "comercial"
        is_support_dashboard = str(widget_prefix).strip().lower() == "soporte"

        st.header(dashboard_name)
        # Render filters
        st.subheader("Filtros")
        selected_year, selected_client, selected_team, selected_criticidad = self._render_filters(df)
        export_tables: List[Tuple[str, pd.DataFrame]] = []

        usage_table = self._render_usage_table(usage_df, selected_year, selected_client)
        if usage_table is not None:
            export_tables.append(("Usabilidad - Actividad", usage_table))
        
        base_filtered = self.filter.filter_by_client(df, selected_client)
        base_filtered = self.filter.filter_by_team(base_filtered, selected_team)
        base_filtered = self.filter.filter_by_criticidad(base_filtered, selected_criticidad)
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
            incidents_table = self._render_incidents_table(base_filtered, selected_year)
            if incidents_table is not None:
                export_tables.append(("Consulta e Incidencias - Flujo", incidents_table))

            cliente_incidencias = self._render_cliente_mensual_section(
                base_filtered,
                selected_year,
                prod_only=True,
                export_chart_label="Consulta e Incidencias - Clientes",
                chart_key_suffix="incidencias_cliente_mensual",
            )
            if cliente_incidencias is not None:
                export_tables.append(("Consulta e Incidencias - Clientes", cliente_incidencias))

            if not is_commercial_dashboard:
                team_table = self._render_team_section(
                    base_filtered,
                    selected_year,
                    prod_only=True,
                    export_chart_label="Consulta e Incidencias - Team",
                    chart_key_suffix="incidencias_team",
                )
                if team_table is not None:
                    export_tables.append(("Consulta e Incidencias - Team", team_table))

            criticidad_table = self._render_criticidad_section(
                base_filtered,
                selected_year,
                prod_only=True,
                export_chart_label="Consulta e Incidencias - Criticidad",
                chart_key_suffix="incidencias_criticidad",
            )
            if criticidad_table is not None:
                export_tables.append(("Consulta e Incidencias - Criticidad", criticidad_table))

            sla_table = self._render_resolucion_section(base_filtered, selected_year)
            if sla_table is not None:
                export_tables.append(("Consulta e Incidencias - SLA", sla_table))

            sla_criticidad_table = self._render_sla_criticidad_section(
                base_filtered,
                selected_year,
                export_chart_label="Consulta e Incidencias - SLA por Criticidad",
                chart_key_suffix="incidencias_sla_criticidad",
            )
            if sla_criticidad_table is not None:
                export_tables.append(("Consulta e Incidencias - SLA por Criticidad", sla_criticidad_table))

            modulo_table = self._render_modulo_section(
                base_filtered,
                selected_year,
                prod_only=True,
                export_chart_label="Consulta e Incidencias - Modulo",
                chart_key_suffix="incidencias_modulo",
            )
            if modulo_table is not None:
                export_tables.append(("Consulta e Incidencias - Modulo", modulo_table))

            if not is_commercial_dashboard:
                ambiente_table = self._render_ambiente_section(
                    base_filtered,
                    selected_year,
                    export_chart_label="Consulta e Incidencias - Ambiente",
                )
                if ambiente_table is not None:
                    export_tables.append(("Consulta e Incidencias - Ambiente", ambiente_table))

            estado_table = self._render_estado_section(
                base_filtered,
                selected_year,
                prod_only=True,
                export_chart_label="Consulta e Incidencias - Estado",
                chart_key_suffix="incidencias_estado",
                commercial_mode=is_commercial_dashboard,
                show_unresolved_ticket_ids=is_support_dashboard,
            )
            if estado_table is not None:
                export_tables.append(("Consulta e Incidencias - Estado", estado_table))

        cambio_base = self.filter.filter_by_client(df, selected_client)
        cambio_base = self.filter.filter_by_team(cambio_base, selected_team)
        cambio_base = self.filter.filter_by_criticidad(cambio_base, selected_criticidad)
        cambio_base = self.filter.filter_by_types(cambio_base, ["Cambio"])
        cambios_prod_only = is_commercial_dashboard

        st.header("KPIs - Solicitudes de Cambio")
        if cambios_prod_only:
            st.subheader("Análisis de tickets en ambientes productivos")
        else:
            st.subheader("Análisis de tickets de TODOS los ambientes")

        if cambio_base.empty:
            st.warning("No hay datos para Solicitudes de Cambio con los filtros seleccionados.")
        else:
            cliente_mensual_cambio = self._render_cliente_mensual_section(
                cambio_base,
                selected_year,
                prod_only=cambios_prod_only,
                export_chart_label="Cambios - Clientes",
                chart_key_suffix="cambios_cliente_mensual",
            )
            if cliente_mensual_cambio is not None:
                export_tables.append(("Cambios - Clientes", cliente_mensual_cambio))

            if not is_commercial_dashboard:
                team_cambio = self._render_team_section(
                    cambio_base,
                    selected_year,
                    prod_only=cambios_prod_only,
                    export_chart_label="Cambios - Team",
                    chart_key_suffix="cambios_team",
                )
                if team_cambio is not None:
                    export_tables.append(("Cambios - Team", team_cambio))

            modulo_cambio = self._render_modulo_section(
                cambio_base,
                selected_year,
                prod_only=cambios_prod_only,
                export_chart_label="Cambios - Modulo",
                chart_key_suffix="cambios_modulo",
            )
            if modulo_cambio is not None:
                export_tables.append(("Cambios - Modulo", modulo_cambio))

            estado_cambio = self._render_estado_section(
                cambio_base,
                selected_year,
                prod_only=cambios_prod_only,
                export_chart_label="Cambios - Estado",
                chart_key_suffix="cambios_estado",
                commercial_mode=is_commercial_dashboard,
            )
            if estado_cambio is not None:
                export_tables.append(("Cambios - Estado", estado_cambio))

        if not is_commercial_dashboard:
            internos_base = self.filter.filter_by_client(df, selected_client)
            internos_base = self.filter.filter_by_team(internos_base, selected_team)
            internos_base = self.filter.filter_by_criticidad(internos_base, selected_criticidad)
            internos_base = self.filter.filter_by_types(internos_base, ["Interno"])

            st.header("KPIs - Solicitudes de Mejoras Técnicas")
            st.subheader("Análisis de tickets de TODOS los ambientes")

            if internos_base.empty:
                st.warning("No hay datos para Solicitudes de Mejoras Técnicas con los filtros seleccionados.")
            else:
                team_interno = self._render_team_section(
                    internos_base,
                    selected_year,
                    prod_only=False,
                    export_chart_label="Internos - Team",
                    chart_key_suffix="internos_team",
                )
                if team_interno is not None:
                    export_tables.append(("Internos - Team", team_interno))

                modulo_interno = self._render_modulo_section(
                    internos_base,
                    selected_year,
                    prod_only=False,
                    export_chart_label="Internos - Modulo",
                    chart_key_suffix="internos_modulo",
                )
                if modulo_interno is not None:
                    export_tables.append(("Internos - Modulo", modulo_interno))

                estado_interno = self._render_estado_section(
                    internos_base,
                    selected_year,
                    prod_only=False,
                    export_chart_label="Internos - Estado",
                    chart_key_suffix="internos_estado",
                    commercial_mode=False,
                )
                if estado_interno is not None:
                    export_tables.append(("Internos - Estado", estado_interno))

        self._render_export_section(
            export_tables,
            selected_year=selected_year,
            selected_client=selected_client,
            selected_team=selected_team,
            selected_criticidad=selected_criticidad,
            dashboard_name=dashboard_name,
        )
    
    def _render_filters(self, df: pd.DataFrame) -> tuple:
        """Render filter controls and return selections."""
        col1, col2, col3, col4 = st.columns(4)
        
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
                    key=self._build_widget_key("filter", "year"),
                    format_func=lambda value: f"{int(value) - 1} - {int(value)}",
                )
                if year_options
                else None
            )
        
        with col2:
            client_options = sorted(df["Grupo"].dropna().unique())
            selected_client = (
                st.multiselect(
                    "Cliente (Grupo)",
                    client_options,
                    default=[],
                    key=self._build_widget_key("filter", "cliente"),
                )
                if client_options
                else []
            )
        
        with col3:
            team_options = sorted(df["Team Asignado"].dropna().unique())
            selected_team = (
                st.multiselect(
                    "Team Asignado",
                    team_options,
                    default=[],
                    key=self._build_widget_key("filter", "team"),
                )
                if team_options
                else []
            )

        with col4:
            criticidad_options = []
            if "Prioridad" in df.columns:
                criticidad_options = sorted(
                    {
                        str(value).strip()
                        for value in df["Prioridad"].dropna().unique()
                        if str(value).strip()
                    }
                )
            selected_criticidad = (
                st.multiselect(
                    "Criticidad",
                    criticidad_options,
                    default=[],
                    key=self._build_widget_key("filter", "criticidad"),
                )
                if criticidad_options
                else []
            )
        
        return selected_year, selected_client, selected_team, selected_criticidad

    def _render_usage_table(
        self,
        usage_df: Optional[pd.DataFrame],
        selected_year: Optional[int],
        selected_client: List[str],
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
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            st.warning("No hay datos de logins para los filtros seleccionados.")
            return None

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
        self._render_table_in_details_expander(display_table, "Usabilidad")

        usage_chart = usage[usage["anio"].isin(years)].copy()
        if not usage_chart.empty:
            usage_fig = self.chart_renderer.render_usage_trend_chart(
                usage_chart,
                None,
                chart_key=self._build_widget_key("chart", "usage_activity"),
            )
            self._export_charts.append(("Usabilidad - Actividad", usage_fig))

        return display_table
    
    def _apply_type_filters(
        self,
        df: pd.DataFrame,
        selected_client: List[str],
        selected_year: Optional[int],
        selected_team: List[str],
        selected_criticidad: List[str],
        types: List[str],
    ) -> pd.DataFrame:
        """Apply client, year, team, criticidad, and ticket type filters."""
        filtered = self.filter.filter_by_client(df, selected_client)
        filtered = self.filter.filter_by_year(filtered, selected_year)
        filtered = self.filter.filter_by_team(filtered, selected_team)
        filtered = self.filter.filter_by_criticidad(filtered, selected_criticidad)
        filtered = self.filter.filter_by_types(filtered, types)
        return filtered

    def _render_export_section(
        self,
        export_tables: List[Tuple[str, pd.DataFrame]],
        selected_year: Optional[int],
        selected_client: List[str],
        selected_team: List[str],
        selected_criticidad: List[str],
        dashboard_name: str,
    ) -> None:
        """Render export buttons for currently displayed tables."""
        if not export_tables:
            return

        st.header("Exportación")
        team_label = ", ".join(selected_team) if selected_team else "Todos"
        client_label = ", ".join(selected_client) if selected_client else "Todos"
        criticidad_label = ", ".join(selected_criticidad) if selected_criticidad else "Todas"
        year_label = str(int(selected_year)) if selected_year is not None else "Todos"
        filters_text = (
            f"Dashboard: {dashboard_name} | Año: {year_label} | Cliente: {client_label} | "
            f"Team Asignado: {team_label} | Criticidad: {criticidad_label}"
        )

        cache = st.session_state.setdefault(self._build_widget_key("export", "cache"), {})
        cache.setdefault("busy", False)
        cache.setdefault("pending_action", None)
        is_busy = bool(cache.get("busy"))

        include_charts = st.toggle(
            "Incluir gráficos en exportación",
            value=False,
            help="Activado: incluye gráficos (consume más memoria, especialmente en PDF). Desactivado: solo tablas (más estable y rápido).",
            disabled=is_busy,
            key=self._build_widget_key("export", "include_charts"),
        )
        chart_payload = self._export_charts if include_charts else None

        signature_parts = [
            year_label,
            client_label,
            team_label,
            criticidad_label,
            str(len(export_tables)),
            f"include_charts={int(include_charts)}",
        ]
        for table_name, table in export_tables:
            numeric_sum = pd.to_numeric(table.stack(), errors="coerce").fillna(0).sum()
            signature_parts.append(f"{table_name}|{table.shape[0]}|{table.shape[1]}|{numeric_sum:.2f}")
        if include_charts:
            signature_parts.append(f"charts_count={len(self._export_charts)}")
            for chart_name, chart_fig in self._export_charts:
                signature_parts.append(f"chart={chart_name}|fig={int(chart_fig is not None)}")
        export_signature = "||".join(str(part) for part in signature_parts)
        excel_signature = f"{export_signature}||format=excel||v=2"
        pdf_signature = f"{export_signature}||format=pdf||v=2"

        if cache.get("excel_signature") != excel_signature:
            cache["excel_signature"] = excel_signature
            cache["excel_bytes"] = None
        if cache.get("pdf_signature") != pdf_signature:
            cache["pdf_signature"] = pdf_signature
            cache["pdf_bytes"] = None

        client_token = ",".join(selected_client) if selected_client else "todos"
        safe_client = TextNormalizer.normalize_column_name(client_token).replace(" ", "_")
        safe_year = year_label.replace(" ", "_")
        safe_dashboard = TextNormalizer.normalize_column_name(dashboard_name).replace(" ", "_")
        filename_base = f"reporte_filtrado_{safe_dashboard}_{safe_client}_{safe_year}"

        col1, col2 = st.columns(2)
        with col1:
            excel_ready = (
                cache.get("excel_bytes") is not None
                and cache.get("excel_signature") == excel_signature
            )
            if not excel_ready:
                if st.button(
                    "Preparar Excel",
                    use_container_width=True,
                    disabled=is_busy,
                    key=self._build_widget_key("export", "prepare_excel"),
                ):
                    cache["busy"] = True
                    cache["pending_action"] = "excel"
                    st.rerun()
            else:
                st.download_button(
                    "Descargar Excel",
                    data=cache["excel_bytes"],
                    file_name=f"{filename_base}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    disabled=is_busy,
                    key=self._build_widget_key("export", "download_excel"),
                )

        with col2:
            pdf_ready = (
                cache.get("pdf_bytes") is not None
                and cache.get("pdf_signature") == pdf_signature
            )
            if not pdf_ready:
                if st.button(
                    "Preparar PDF",
                    use_container_width=True,
                    disabled=is_busy,
                    key=self._build_widget_key("export", "prepare_pdf"),
                ):
                    cache["busy"] = True
                    cache["pending_action"] = "pdf"
                    st.rerun()
            else:
                st.download_button(
                    "Descargar PDF",
                    data=cache["pdf_bytes"],
                    file_name=f"{filename_base}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    disabled=is_busy,
                    key=self._build_widget_key("export", "download_pdf"),
                )

        pending_action = cache.get("pending_action")
        if cache.get("busy") and pending_action in {"excel", "pdf"}:
            try:
                if pending_action == "excel":
                    with st.spinner("Generando archivo Excel..."):
                        cache["excel_bytes"] = self.export_builder.build_excel_bytes(
                            export_tables,
                            charts=chart_payload,
                        )
                else:
                    with st.spinner("Generando archivo PDF..."):
                        cache["pdf_bytes"] = self.export_builder.build_pdf_bytes(
                            export_tables,
                            title=f"Informes Gerenciales de Tickets - {dashboard_name}",
                            filters_text=filters_text,
                            charts=chart_payload,
                        )
            except ImportError:
                st.info("Para exportar PDF instala dependencias con: pip install -r requirements.txt")
            finally:
                cache["busy"] = False
                cache["pending_action"] = None
            st.rerun()
    
    def _render_incidents_table(
        self, base_filtered: pd.DataFrame, selected_year: Optional[int]
    ) -> Optional[pd.DataFrame]:
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
                st.info(f"ℹ️ No hay datos para el año {year}")
                continue

            table = self.table_builder.build_monthly_counts_table(created_counts, resolved_counts)
            year_row = pd.DataFrame(
                [{col: pd.NA for col in table.columns}],
                index=[f"~~ AÑO {year} ~~"],
            )
            tables.extend([year_row, table])

        if not tables:
            st.warning("No hay datos para Flujo de tickets con los filtros seleccionados.")
            return None

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
            if flow_fig is not None:
                self._export_charts.append(("Consulta e Incidencias - Flujo", flow_fig))

        return display_table
    
    def _render_team_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "team",
    ) -> Optional[pd.DataFrame]:
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
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            st.warning("No hay datos para KPI - Team Asignado con los filtros seleccionados.")
            return None

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
            if team_fig is not None:
                chart_label = export_chart_label or "KPI - Team Asignado"
                self._export_charts.append((chart_label, team_fig))

        return display_table

    def _render_cliente_mensual_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "cliente_mensual",
    ) -> Optional[pd.DataFrame]:
        """Render monthly ticket count by client section."""
        st.subheader("KPI - Cliente")
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
            st.warning("No hay datos para KPI - Cliente con los filtros seleccionados.")
            return None

        combined_table = pd.concat(tables)
        combined_table.index.name = "Cliente"
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
            if cliente_fig is not None:
                chart_label = export_chart_label or "KPI - Cliente"
                self._export_charts.append((chart_label, cliente_fig))

        return display_table

    def _render_criticidad_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "criticidad",
    ) -> Optional[pd.DataFrame]:
        """Render criticidad analysis section based on ticket priority."""
        st.subheader("KPI - Criticidad")
        current_year = selected_year or pd.Timestamp.today().year
        years = [current_year - 1, current_year]
        priority_label_map = {
            "urgente": "Urgente",
            "urgent": "Urgente",
            "alta": "Alta",
            "high": "Alta",
            "media": "Media",
            "medium": "Media",
            "baja": "Baja",
            "low": "Baja",
        }

        tables = []
        for year in years:
            year_df = self.filter.filter_by_year(base_filtered, year)
            if prod_only:
                year_df = self.filter.filter_production_environment(year_df)
            if year_df.empty:
                st.info(f"ℹ️ No hay datos para el año {year}")
                continue

            year_df = year_df.copy()
            priority_norm = year_df["Prioridad"].astype(str).str.strip().str.lower()
            year_df["Prioridad"] = priority_norm.map(priority_label_map).fillna("Sin criticidad")

            pivot = self.table_builder.build_pivot_table(
                year_df, "Prioridad", "Sin criticidad"
            )
            priority_order_map = {
                "urgente": 0,
                "urgent": 0,
                "alta": 1,
                "high": 1,
                "media": 2,
                "medium": 2,
                "baja": 3,
                "low": 3,
            }
            if "Total" in pivot.index:
                total_row = pivot.loc[["Total"]]
                pivot_body = pivot.drop(index="Total")
            else:
                total_row = None
                pivot_body = pivot

            priority_labels = pivot_body.index.to_series().astype(str)
            priority_sort = priority_labels.str.strip().str.lower().map(priority_order_map).fillna(99)
            tie_breaker = priority_labels.str.strip().str.lower()
            pivot_body = pivot_body.assign(_prio_sort=priority_sort.values, _prio_tie=tie_breaker.values)
            pivot_body = pivot_body.sort_values(by=["_prio_sort", "_prio_tie"]).drop(columns=["_prio_sort", "_prio_tie"])

            if total_row is not None:
                pivot = pd.concat([pivot_body, total_row])
            else:
                pivot = pivot_body

            year_row = pd.DataFrame(
                [{col: pd.NA for col in pivot.columns}],
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            st.warning("No hay datos para KPI - Criticidad con los filtros seleccionados.")
            return None

        combined_table = pd.concat(tables)
        combined_table.index.name = "Prioridad"
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
        self._render_table_in_details_expander(display_table, "Criticidad")

        chart_years = [current_year - 1, current_year]
        chart_df = base_filtered[base_filtered["Año"].isin(chart_years)].copy()
        if prod_only:
            chart_df = self.filter.filter_production_environment(chart_df)
        if not chart_df.empty:
            chart_df = chart_df.copy()
            chart_priority_norm = chart_df["Prioridad"].astype(str).str.strip().str.lower()
            chart_df["Prioridad"] = chart_priority_norm.map(priority_label_map).fillna("Sin criticidad")
            chart_priority_labels = chart_df["Prioridad"].astype(str).str.strip()
            chart_priority_sort = chart_priority_labels.str.lower().map(priority_order_map).fillna(99)
            chart_priority_order = (
                pd.DataFrame(
                    {
                        "label": chart_priority_labels,
                        "sort": chart_priority_sort,
                        "tie": chart_priority_labels.str.lower(),
                    }
                )
                .drop_duplicates(subset=["label"])
                .sort_values(by=["sort", "tie"])["label"]
                .tolist()
            )
            criticidad_fig = self.chart_renderer.render_trend_chart(
                chart_df,
                "Prioridad",
                None,
                chart_key=self._build_widget_key("chart", chart_key_suffix),
                category_order=chart_priority_order,
            )
            if criticidad_fig is not None:
                chart_label = export_chart_label or "KPI - Criticidad"
                self._export_charts.append((chart_label, criticidad_fig))

        return display_table

    def _render_estado_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "estado",
        commercial_mode: bool = False,
        show_unresolved_ticket_ids: bool = False,
    ) -> Optional[pd.DataFrame]:
        """Render estado (status) analysis section."""
        st.subheader("KPI - Estado")
        current_year = selected_year or pd.Timestamp.today().year
        years = [current_year - 1, current_year]
        commercial_status_order = ["Pendiente", "En progreso", "Resuelto"]

        tables = []
        for year in years:
            year_df = self.filter.filter_by_year(base_filtered, year)
            if prod_only:
                year_df = self.filter.filter_production_environment(year_df)
            if year_df.empty:
                st.info(f"ℹ️ No hay datos para el año {year}")
                continue

            year_df = self._build_estado_grouped(year_df, "Estado Agrupado")

            if commercial_mode:
                estado_series = year_df["Estado Agrupado"].fillna("").astype(str).str.strip().str.lower()
                estado_comercial = pd.Series(pd.NA, index=year_df.index, dtype="object")
                estado_comercial = estado_comercial.mask(
                    estado_series.str.contains("pendiente", na=False),
                    "Pendiente",
                )
                estado_comercial = estado_comercial.mask(
                    estado_series.str.contains("progreso", na=False),
                    "En progreso",
                )
                estado_comercial = estado_comercial.mask(
                    estado_series.eq("resuelto") | estado_series.str.contains("resuelto|cerrado|solucionado", na=False),
                    "Resuelto",
                )

                estado_df = year_df.copy()
                estado_df["Estado Comercial"] = estado_comercial
                estado_df = estado_df.dropna(subset=["Estado Comercial"])

                month_order = list(range(1, 13))
                if estado_df.empty:
                    pivot = pd.DataFrame(0, index=commercial_status_order, columns=month_order)
                else:
                    pivot = (
                        estado_df.pivot_table(
                            index="Estado Comercial",
                            columns="Mes",
                            values="ID del ticket",
                            aggfunc="nunique",
                            fill_value=0,
                        )
                        .reindex(index=commercial_status_order, fill_value=0)
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
            st.warning("No hay datos para KPI - Estado con los filtros seleccionados.")
            return None

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
                    unresolved_detail = detail_df.loc[unresolved_mask, ["ID del ticket", "Hora de creacion", "Mes", "Año"]].copy()
                    unresolved_detail["ID del ticket"] = (
                        unresolved_detail["ID del ticket"]
                        .astype(str)
                        .str.strip()
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
                            .agg(
                                casos=("ID del ticket", lambda values: sorted(pd.unique(values).tolist())),
                            )
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
                estado_series = chart_df["Estado Agrupado"].fillna("").astype(str).str.strip().str.lower()
                estado_comercial = pd.Series(pd.NA, index=chart_df.index, dtype="object")
                estado_comercial = estado_comercial.mask(
                    estado_series.str.contains("pendiente", na=False),
                    "Pendiente",
                )
                estado_comercial = estado_comercial.mask(
                    estado_series.str.contains("progreso", na=False),
                    "En progreso",
                )
                estado_comercial = estado_comercial.mask(
                    estado_series.eq("resuelto") | estado_series.str.contains("resuelto|cerrado|solucionado", na=False),
                    "Resuelto",
                )
                chart_df = chart_df.copy()
                chart_df["Estado Comercial"] = estado_comercial
                chart_df = chart_df.dropna(subset=["Estado Comercial"])
                category_col = "Estado Comercial"
                category_order = commercial_status_order

            estado_fig = self.chart_renderer.render_trend_chart(
                chart_df,
                category_col,
                None,
                chart_key=self._build_widget_key("chart", chart_key_suffix),
                category_order=category_order,
            )
            if estado_fig is not None:
                chart_label = export_chart_label or "KPI - Estado"
                self._export_charts.append((chart_label, estado_fig))

        return display_table

    def _render_modulo_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "modulo",
    ) -> Optional[pd.DataFrame]:
        """Render modulo (module) analysis section."""
        st.subheader("KPI - Módulo")
        current_year = selected_year or pd.Timestamp.today().year
        years = [current_year - 1, current_year]
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
                st.info(f"ℹ️ No hay datos para el año {year}")
                continue
            pivot = self.table_builder.build_pivot_table(year_df, "Modulo", "Sin módulo")

            if top_modules:
                available_modules = [module for module in top_modules if module in pivot.index]
                pivot = pivot.loc[available_modules]
                if pivot.empty:
                    st.info(f"ℹ️ No hay datos de módulos TOP 5 para el año {year}")
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
            st.warning("No hay datos para KPI - Módulo con los filtros seleccionados.")
            return None

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
                if modulo_fig is not None:
                    chart_label = export_chart_label or "KPI - Módulo"
                    self._export_charts.append((chart_label, modulo_fig))

        return display_table

    def _render_ambiente_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        export_chart_label: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
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
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            st.warning("No hay datos para KPI - Ambiente con los filtros seleccionados.")
            return None

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
            if ambiente_fig is not None:
                chart_label = export_chart_label or "KPI - Ambiente"
                self._export_charts.append((chart_label, ambiente_fig))

        return display_table

    def _render_resolucion_section(
        self, base_filtered: pd.DataFrame, selected_year: Optional[int]
    ) -> Optional[pd.DataFrame]:
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
                index=[f"~~ AÑO {year} ~~"],
            )
            year_row.index.name = pivot.index.name
            tables.extend([year_row, pivot])

        if not tables:
            st.warning("No hay datos para KPI - SLA con los filtros seleccionados.")
            return None

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
            sla_fig = self.chart_renderer.render_trend_chart(
                chart_df,
                "Estado de resolucion",
                None,
                chart_key=self._build_widget_key("chart", "sla"),
            )
            if sla_fig is not None:
                self._export_charts.append(("Consulta e Incidencias - SLA", sla_fig))

        return formatted_table

    def _render_sla_criticidad_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "sla_criticidad",
    ) -> Optional[pd.DataFrame]:
        """Render SLA by criticidad section based on resolution date."""
        st.subheader("KPI - SLA por Criticidad")
        current_year = selected_year or pd.Timestamp.today().year
        years = [current_year - 1, current_year]

        priority_order_map = {
            "urgente": 0,
            "urgent": 0,
            "alta": 1,
            "high": 1,
            "media": 2,
            "medium": 2,
            "baja": 3,
            "low": 3,
        }
        priority_label_map = {
            "urgente": "Urgente",
            "urgent": "Urgente",
            "alta": "Alta",
            "high": "Alta",
            "media": "Media",
            "medium": "Media",
            "baja": "Baja",
            "low": "Baja",
        }
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
                st.info(f"ℹ️ No hay datos para el año {year}. Se muestran valores en 0.")
                pivot_body = build_zero_pivot()
                year_row = pd.DataFrame(
                    [{col: pd.NA for col in pivot_body.columns}],
                    index=[f"~~ AÑO {year} ~~"],
                )
                year_row.index.name = pivot_body.index.name
                tables.extend([year_row, pivot_body])
                continue

            sla_prod = sla_prod.copy()
            estado_norm = sla_prod["Estado de resolucion"].astype(str).str.strip().str.lower()
            sla_prod["SLA Estado"] = ""
            sla_prod.loc[estado_norm == "within sla", "SLA Estado"] = "Cumplido"
            sla_prod.loc[estado_norm == "sla violated", "SLA Estado"] = "Incumplido"
            sla_prod = sla_prod[sla_prod["SLA Estado"].isin(["Cumplido", "Incumplido"])]
            if sla_prod.empty:
                st.info(f"ℹ️ No hay datos de SLA para el año {year}. Se muestran valores en 0.")
                pivot_body = build_zero_pivot()
                year_row = pd.DataFrame(
                    [{col: pd.NA for col in pivot_body.columns}],
                    index=[f"~~ AÑO {year} ~~"],
                )
                year_row.index.name = pivot_body.index.name
                tables.extend([year_row, pivot_body])
                continue

            prioridad_norm = sla_prod["Prioridad"].astype(str).str.strip().str.lower()
            sla_prod["Prioridad ES"] = prioridad_norm.map(priority_label_map)
            sla_prod = sla_prod.dropna(subset=["Prioridad ES"])
            if sla_prod.empty:
                st.info(f"ℹ️ No hay criticidades válidas para el año {year}. Se muestran valores en 0.")
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
            if "Total" in pivot.index:
                total_row = pivot.loc[["Total"]]
                pivot_body = pivot.drop(index="Total")
            else:
                total_row = None
                pivot_body = pivot

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
            priority_sort = priority_part.str.lower().map(priority_order_map).fillna(99)
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
            st.warning("No hay datos para KPI - SLA por Criticidad con los filtros seleccionados.")
            return None

        combined_table = pd.concat(tables)
        combined_table.index.name = "SLA - Criticidad"
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
            chart_priority_sort = chart_priority.str.lower().map(priority_order_map).fillna(99)
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
            if chart_fig is not None:
                chart_label = export_chart_label or "KPI - SLA por Criticidad"
                self._export_charts.append((chart_label, chart_fig))

        return display_table
