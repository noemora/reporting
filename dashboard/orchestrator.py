"""Dashboard orchestration and coordination."""
from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st

from config import AppConfig
from data import DataFilter
from services import ExportBuilder, ExportStateManager, TableBuilder
from ui import ChartRenderer
from utils import TeamFilterHelper, TicketStatusHelper

from .sections_renderer import SectionsRenderer
from .usage_renderer import UsageRenderer


class DashboardOrchestrator:
    """Orquesta el flujo principal del dashboard y delega responsabilidades."""

    SUPPORT_TEAM_UNIFIED_LABEL = "Soporte"

    def __init__(self, config: AppConfig):
        self.config = config
        self.filter = DataFilter(config)
        self.table_builder = TableBuilder(config)
        self.export_builder = ExportBuilder()
        self.export_state_manager = ExportStateManager()
        self.chart_renderer = ChartRenderer(config)
        self.status_helper = TicketStatusHelper(config)
        self.team_filter_helper = TeamFilterHelper(self.SUPPORT_TEAM_UNIFIED_LABEL)
        self.usage_renderer = UsageRenderer(config, self.chart_renderer)
        self.sections_renderer = SectionsRenderer(
            config=config,
            data_filter=self.filter,
            table_builder=self.table_builder,
            chart_renderer=self.chart_renderer,
        )

    @staticmethod
    def _render_table_in_details_expander(table: pd.DataFrame, section_label: str) -> None:
        """Render a table inside a details expander."""
        with st.expander(f"Ver detalles - {section_label}", expanded=False):
            st.table(table)

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

        self.sections_renderer.set_runtime(
            build_widget_key=self._build_widget_key,
            render_table_in_details_expander=self._render_table_in_details_expander,
            export_charts=self._export_charts,
            build_resolved_mask=self.status_helper.build_resolved_mask,
            build_estado_grouped=self.status_helper.build_estado_grouped,
            normalize_resolution_status_for_display=self.status_helper.normalize_resolution_status_for_display,
        )

        st.header(dashboard_name)
        st.subheader("Filtros")
        (
            selected_year,
            selected_client,
            selected_team_labels,
            selected_team_values,
            selected_criticidad,
        ) = self._render_filters(df, commercial_mode=is_commercial_dashboard)
        export_tables: List[Tuple[str, pd.DataFrame]] = []

        usage_table = self.usage_renderer.render_usage_table(
            usage_df=usage_df,
            selected_year=selected_year,
            selected_client=selected_client,
            build_widget_key=self._build_widget_key,
            render_table_in_details_expander=self._render_table_in_details_expander,
            export_charts=self._export_charts,
        )
        if usage_table is not None:
            export_tables.append(("Usabilidad - Actividad", usage_table))

        base_filtered = self.filter.filter_by_client(df, selected_client)
        base_filtered = self.filter.filter_by_team(base_filtered, selected_team_values)
        base_filtered = self.filter.filter_by_criticidad(base_filtered, selected_criticidad)
        base_filtered = self.filter.filter_by_types(
            base_filtered, ["Consulta de informacion", "Incidencia"]
        )

        st.header("KPIs - Consulta de Informacion e Incidencias")
        st.subheader("Análisis de tickets en ambientes productivos")

        if base_filtered.empty:
            st.warning("No hay datos para Consulta de Informacion e Incidencias con los filtros seleccionados.")
        else:
            incidents_table = self.sections_renderer.render_incidents_table(base_filtered, selected_year)
            if incidents_table is not None:
                export_tables.append(("Consulta e Incidencias - Flujo", incidents_table))

            cliente_incidencias = self.sections_renderer.render_cliente_mensual_section(
                base_filtered,
                selected_year,
                prod_only=True,
                export_chart_label="Consulta e Incidencias - Clientes",
                chart_key_suffix="incidencias_cliente_mensual",
            )
            if cliente_incidencias is not None:
                export_tables.append(("Consulta e Incidencias - Clientes", cliente_incidencias))

            if not is_commercial_dashboard:
                team_table = self.sections_renderer.render_team_section(
                    base_filtered,
                    selected_year,
                    prod_only=True,
                    export_chart_label="Consulta e Incidencias - Team",
                    chart_key_suffix="incidencias_team",
                )
                if team_table is not None:
                    export_tables.append(("Consulta e Incidencias - Team", team_table))

            criticidad_table = self.sections_renderer.render_criticidad_section(
                base_filtered,
                selected_year,
                prod_only=True,
                export_chart_label="Consulta e Incidencias - Criticidad",
                chart_key_suffix="incidencias_criticidad",
            )
            if criticidad_table is not None:
                export_tables.append(("Consulta e Incidencias - Criticidad", criticidad_table))

            sla_table = self.sections_renderer.render_resolucion_section(base_filtered, selected_year)
            if sla_table is not None:
                export_tables.append(("Consulta e Incidencias - SLA", sla_table))

            sla_criticidad_table = self.sections_renderer.render_sla_criticidad_section(
                base_filtered,
                selected_year,
                export_chart_label="Consulta e Incidencias - SLA por Criticidad",
                chart_key_suffix="incidencias_sla_criticidad",
            )
            if sla_criticidad_table is not None:
                export_tables.append(("Consulta e Incidencias - SLA por Criticidad", sla_criticidad_table))

            modulo_table = self.sections_renderer.render_modulo_section(
                base_filtered,
                selected_year,
                prod_only=True,
                export_chart_label="Consulta e Incidencias - Modulo",
                chart_key_suffix="incidencias_modulo",
            )
            if modulo_table is not None:
                export_tables.append(("Consulta e Incidencias - Modulo", modulo_table))

            if not is_commercial_dashboard:
                ambiente_table = self.sections_renderer.render_ambiente_section(
                    base_filtered,
                    selected_year,
                    export_chart_label="Consulta e Incidencias - Ambiente",
                )
                if ambiente_table is not None:
                    export_tables.append(("Consulta e Incidencias - Ambiente", ambiente_table))

            estado_table = self.sections_renderer.render_estado_section(
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
        cambio_base = self.filter.filter_by_team(cambio_base, selected_team_values)
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
            cliente_mensual_cambio = self.sections_renderer.render_cliente_mensual_section(
                cambio_base,
                selected_year,
                prod_only=cambios_prod_only,
                export_chart_label="Cambios - Clientes",
                chart_key_suffix="cambios_cliente_mensual",
            )
            if cliente_mensual_cambio is not None:
                export_tables.append(("Cambios - Clientes", cliente_mensual_cambio))

            if not is_commercial_dashboard:
                team_cambio = self.sections_renderer.render_team_section(
                    cambio_base,
                    selected_year,
                    prod_only=cambios_prod_only,
                    export_chart_label="Cambios - Team",
                    chart_key_suffix="cambios_team",
                )
                if team_cambio is not None:
                    export_tables.append(("Cambios - Team", team_cambio))

            modulo_cambio = self.sections_renderer.render_modulo_section(
                cambio_base,
                selected_year,
                prod_only=cambios_prod_only,
                export_chart_label="Cambios - Modulo",
                chart_key_suffix="cambios_modulo",
            )
            if modulo_cambio is not None:
                export_tables.append(("Cambios - Modulo", modulo_cambio))

            estado_cambio = self.sections_renderer.render_estado_section(
                cambio_base,
                selected_year,
                prod_only=cambios_prod_only,
                export_chart_label="Cambios - Estado",
                chart_key_suffix="cambios_estado",
                commercial_mode=False,
            )
            if estado_cambio is not None:
                export_tables.append(("Cambios - Estado", estado_cambio))

        if not is_commercial_dashboard:
            internos_base = self.filter.filter_by_client(df, selected_client)
            internos_base = self.filter.filter_by_team(internos_base, selected_team_values)
            internos_base = self.filter.filter_by_criticidad(internos_base, selected_criticidad)
            internos_base = self.filter.filter_by_types(internos_base, ["Interno"])

            st.header("KPIs - Solicitudes de Mejoras Técnicas")
            st.subheader("Análisis de tickets de TODOS los ambientes")

            if internos_base.empty:
                st.warning("No hay datos para Solicitudes de Mejoras Técnicas con los filtros seleccionados.")
            else:
                team_interno = self.sections_renderer.render_team_section(
                    internos_base,
                    selected_year,
                    prod_only=False,
                    export_chart_label="Internos - Team",
                    chart_key_suffix="internos_team",
                )
                if team_interno is not None:
                    export_tables.append(("Internos - Team", team_interno))

                modulo_interno = self.sections_renderer.render_modulo_section(
                    internos_base,
                    selected_year,
                    prod_only=False,
                    export_chart_label="Internos - Modulo",
                    chart_key_suffix="internos_modulo",
                )
                if modulo_interno is not None:
                    export_tables.append(("Internos - Modulo", modulo_interno))

                estado_interno = self.sections_renderer.render_estado_section(
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
            selected_team=selected_team_labels,
            selected_criticidad=selected_criticidad,
            dashboard_name=dashboard_name,
        )

    def _render_filters(self, df: pd.DataFrame, commercial_mode: bool = False) -> tuple:
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
            team_options, team_option_map = self.team_filter_helper.build_team_filter_config(df, commercial_mode)
            selected_team_labels = (
                st.multiselect(
                    "Team Asignado",
                    team_options,
                    default=[],
                    key=self._build_widget_key("filter", "team"),
                )
                if team_options
                else []
            )
            selected_team_values = self.team_filter_helper.resolve_selected_team_values(
                selected_team_labels,
                team_option_map,
            )

        with col4:
            criticidad_options = self.filter.get_criticidad_options(df)
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

        return selected_year, selected_client, selected_team_labels, selected_team_values, selected_criticidad

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
        labels = self.export_state_manager.build_filter_labels(
            selected_year=selected_year,
            selected_client=selected_client,
            selected_team=selected_team,
            selected_criticidad=selected_criticidad,
        )
        year_label = labels["year"]
        filters_text = self.export_state_manager.build_filters_text(dashboard_name, labels)

        cache = st.session_state.setdefault(self._build_widget_key("export", "cache"), {})
        self.export_state_manager.ensure_cache(cache)
        is_busy = bool(cache.get("busy"))

        include_charts = st.toggle(
            "Incluir gráficos en exportación",
            value=False,
            help="Activado: incluye gráficos (consume más memoria, especialmente en PDF). Desactivado: solo tablas (más estable y rápido).",
            disabled=is_busy,
            key=self._build_widget_key("export", "include_charts"),
        )
        chart_payload = self._export_charts if include_charts else None

        excel_signature, pdf_signature = self.export_state_manager.build_signatures(
            export_tables=export_tables,
            chart_payload=chart_payload,
            labels=labels,
        )
        self.export_state_manager.reset_cache_if_signature_changed(
            cache=cache,
            excel_signature=excel_signature,
            pdf_signature=pdf_signature,
        )

        filename_base = self.export_state_manager.build_filename_base(
            dashboard_name=dashboard_name,
            selected_client=selected_client,
            year_label=year_label,
        )

        col1, col2 = st.columns(2)
        with col1:
            excel_ready = self.export_state_manager.is_excel_ready(cache, excel_signature)
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
            pdf_ready = self.export_state_manager.is_pdf_ready(cache, pdf_signature)
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
