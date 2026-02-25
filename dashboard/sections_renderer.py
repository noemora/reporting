"""KPI sections facade that delegates rendering by domain."""
from typing import Callable, List, Optional, Tuple

import pandas as pd

from config import AppConfig
from data import DataFilter
from services import TableBuilder
from ui import ChartRenderer

from .distribution_renderer import DistributionSectionsRenderer
from .sla_renderer import SlaSectionsRenderer
from .status_renderer import StatusSectionsRenderer


class SectionsRenderer:
    """Facade para secciones KPI, delegando por dominio funcional."""

    def __init__(
        self,
        config: AppConfig,
        data_filter: DataFilter,
        table_builder: TableBuilder,
        chart_renderer: ChartRenderer,
    ):
        self.distribution_renderer = DistributionSectionsRenderer(
            config=config,
            data_filter=data_filter,
            table_builder=table_builder,
            chart_renderer=chart_renderer,
        )
        self.status_renderer = StatusSectionsRenderer(
            config=config,
            data_filter=data_filter,
            table_builder=table_builder,
            chart_renderer=chart_renderer,
        )
        self.sla_renderer = SlaSectionsRenderer(
            config=config,
            data_filter=data_filter,
            table_builder=table_builder,
            chart_renderer=chart_renderer,
        )

    def set_runtime(
        self,
        build_widget_key: Callable[..., str],
        render_table_in_details_expander: Callable[[pd.DataFrame, str], None],
        export_charts: List[Tuple[str, object]],
        build_resolved_mask: Callable[[pd.DataFrame], pd.Series],
        build_estado_grouped: Callable[[pd.DataFrame, str], pd.DataFrame],
        normalize_resolution_status_for_display: Callable[[pd.Series], pd.Series],
    ) -> None:
        runtime_args = {
            "build_widget_key": build_widget_key,
            "render_table_in_details_expander": render_table_in_details_expander,
            "export_charts": export_charts,
            "build_resolved_mask": build_resolved_mask,
            "build_estado_grouped": build_estado_grouped,
            "normalize_resolution_status_for_display": normalize_resolution_status_for_display,
        }
        self.distribution_renderer.set_runtime(**runtime_args)
        self.status_renderer.set_runtime(**runtime_args)
        self.sla_renderer.set_runtime(**runtime_args)

    def render_incidents_table(
        self, base_filtered: pd.DataFrame, selected_year: Optional[int]
    ) -> Optional[pd.DataFrame]:
        return self.distribution_renderer.render_incidents_table(base_filtered, selected_year)

    def render_team_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "team",
    ) -> Optional[pd.DataFrame]:
        return self.distribution_renderer.render_team_section(
            base_filtered=base_filtered,
            selected_year=selected_year,
            prod_only=prod_only,
            export_chart_label=export_chart_label,
            chart_key_suffix=chart_key_suffix,
        )

    def render_cliente_mensual_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "cliente_mensual",
    ) -> Optional[pd.DataFrame]:
        return self.distribution_renderer.render_cliente_mensual_section(
            base_filtered=base_filtered,
            selected_year=selected_year,
            prod_only=prod_only,
            export_chart_label=export_chart_label,
            chart_key_suffix=chart_key_suffix,
        )

    def render_criticidad_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "criticidad",
    ) -> Optional[pd.DataFrame]:
        return self.distribution_renderer.render_criticidad_section(
            base_filtered=base_filtered,
            selected_year=selected_year,
            prod_only=prod_only,
            export_chart_label=export_chart_label,
            chart_key_suffix=chart_key_suffix,
        )

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
        return self.status_renderer.render_estado_section(
            base_filtered=base_filtered,
            selected_year=selected_year,
            prod_only=prod_only,
            export_chart_label=export_chart_label,
            chart_key_suffix=chart_key_suffix,
            commercial_mode=commercial_mode,
            show_unresolved_ticket_ids=show_unresolved_ticket_ids,
        )

    def render_modulo_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        prod_only: bool,
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "modulo",
    ) -> Optional[pd.DataFrame]:
        return self.distribution_renderer.render_modulo_section(
            base_filtered=base_filtered,
            selected_year=selected_year,
            prod_only=prod_only,
            export_chart_label=export_chart_label,
            chart_key_suffix=chart_key_suffix,
        )

    def render_ambiente_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        export_chart_label: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        return self.distribution_renderer.render_ambiente_section(
            base_filtered=base_filtered,
            selected_year=selected_year,
            export_chart_label=export_chart_label,
        )

    def render_resolucion_section(
        self, base_filtered: pd.DataFrame, selected_year: Optional[int]
    ) -> Optional[pd.DataFrame]:
        return self.sla_renderer.render_resolucion_section(base_filtered, selected_year)

    def render_sla_criticidad_section(
        self,
        base_filtered: pd.DataFrame,
        selected_year: Optional[int],
        export_chart_label: Optional[str] = None,
        chart_key_suffix: str = "sla_criticidad",
    ) -> Optional[pd.DataFrame]:
        return self.sla_renderer.render_sla_criticidad_section(
            base_filtered=base_filtered,
            selected_year=selected_year,
            export_chart_label=export_chart_label,
            chart_key_suffix=chart_key_suffix,
        )
