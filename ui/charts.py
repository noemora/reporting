"""Chart rendering functionality."""
from typing import List, Optional
import pandas as pd
import plotly.express as px
import streamlit as st

from config import AppConfig


class ChartRenderer:
    """Renders various chart visualizations."""
    
    def __init__(self, config: AppConfig):
        self.config = config
    
    def render_trend_chart(
        self,
        df: pd.DataFrame,
        category_col: str,
        selected_year: Optional[int],
        chart_key: Optional[str] = None,
        category_order: Optional[List[str]] = None,
    ) -> px.line:
        """Render a monthly trend chart with labels."""
        trend = self._prepare_trend_data(df, category_col, selected_year, category_order)
        fig = self._create_line_chart(trend, category_col, category_order)
        
        st.plotly_chart(fig, width="stretch", key=chart_key)
        return fig

    def render_usage_trend_chart(
        self,
        usage: pd.DataFrame,
        selected_year: Optional[int],
        chart_key: Optional[str] = None,
    ) -> px.line:
        """Render a monthly logins trend chart with labels."""
        trend = self._prepare_usage_trend_data(usage, selected_year)
        fig = self._create_usage_line_chart(trend)

        st.plotly_chart(fig, width="stretch", key=chart_key)
        return fig
    
    def render_flow_chart(
        self,
        flow: pd.DataFrame,
        chart_key: Optional[str] = None,
    ) -> Optional[px.line]:
        """Render a monthly flow chart for created vs resolved tickets."""
        if flow.empty:
            return None
        fig = self._create_flow_line_chart(flow)
        st.plotly_chart(fig, width="stretch", key=chart_key)
        return fig
    
    def _prepare_trend_data(
        self,
        df: pd.DataFrame,
        category_col: str,
        selected_year: Optional[int],
        category_order: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Prepare trend data for visualization."""
        if category_col == "Estado de resolucion":
            df = df.copy()
            # Normalize Estado de resolucion values (already normalized in orchestrator)
            # This is just for consistency if called from elsewhere
            def normalize_resolution_status(value):
                if pd.isna(value):
                    return "Sin estado de resolución"
                str_value = str(value).strip().lower()
                if not str_value or str_value == "nan" or str_value == "":
                    return "Sin estado de resolución"
                elif str_value in {"within sla", "cumplido", "en sla", "dentro de sla"}:
                    return "Cumplido"
                elif str_value in {"sla violated", "incumplido", "fuera de sla"}:
                    return "Incumplido"
                elif str_value in {"resuelto", "resolved", "solucionado", "cerrado", "closed"}:
                    return "Resuelto"
                else:
                    return value
            
            df[category_col] = df[category_col].apply(normalize_resolution_status)
        
        trend = (
            df.groupby(["Periodo", category_col])["ID del ticket"]
            .nunique()
            .reset_index()
        )
        
        if selected_year is not None:
            today = pd.Timestamp.today()
            end_month = 12
            if int(selected_year) == today.year:
                end_month = today.month
            all_months = pd.date_range(
                start=f"{int(selected_year)}-01-01",
                end=f"{int(selected_year)}-{end_month:02d}-01",
                freq="MS",
            )
        else:
            # Para múltiples años, crear rango completo para cada año presente
            today = pd.Timestamp.today()
            years_in_data = pd.to_datetime(df["Periodo"].dropna()).dt.year.unique()
            all_months = []
            for year in sorted(years_in_data):
                end_month = 12
                if int(year) == today.year:
                    end_month = today.month
                all_months.extend(pd.date_range(
                    start=f"{int(year)}-01-01",
                    end=f"{int(year)}-{end_month:02d}-01",
                    freq="MS",
                ))
            all_months = pd.to_datetime(all_months)
        
        detected_categories = [str(value) for value in df[category_col].dropna().unique()]
        if category_order:
            ordered_base = list(dict.fromkeys([str(cat) for cat in category_order]))
            remaining = sorted([cat for cat in detected_categories if cat not in ordered_base])
            all_categories = ordered_base + remaining
        else:
            all_categories = sorted(detected_categories)
        full_index = pd.MultiIndex.from_product(
            [all_months, all_categories],
            names=["Periodo", category_col],
        )
        trend = (
            trend.set_index(["Periodo", category_col])
            .reindex(full_index, fill_value=0)
            .reset_index()
        )
        
        return trend

    def _prepare_usage_trend_data(
        self, usage: pd.DataFrame, selected_year: Optional[int]
    ) -> pd.DataFrame:
        """Prepare logins trend data for visualization."""
        usage = usage.copy()
        usage["Periodo"] = pd.to_datetime(
            dict(year=usage["anio"], month=usage["mes_num"], day=1), errors="coerce"
        )
        trend = (
            usage.groupby(["Periodo", "Cliente"])["logins"]
            .sum()
            .reset_index()
        )

        if selected_year is not None:
            today = pd.Timestamp.today()
            end_month = 12
            if int(selected_year) == today.year:
                end_month = today.month
            all_months = pd.date_range(
                start=f"{int(selected_year)}-01-01",
                end=f"{int(selected_year)}-{end_month:02d}-01",
                freq="MS",
            )
        else:
            today = pd.Timestamp.today()
            years_in_data = pd.to_datetime(trend["Periodo"].dropna()).dt.year.unique()
            all_months = []
            for year in sorted(years_in_data):
                end_month = 12
                if int(year) == today.year:
                    end_month = today.month
                all_months.extend(
                    pd.date_range(
                        start=f"{int(year)}-01-01",
                        end=f"{int(year)}-{end_month:02d}-01",
                        freq="MS",
                    )
                )
            all_months = pd.to_datetime(all_months)

        all_clients = sorted(trend["Cliente"].dropna().unique())
        full_index = pd.MultiIndex.from_product(
            [all_months, all_clients],
            names=["Periodo", "Cliente"],
        )
        trend = (
            trend.set_index(["Periodo", "Cliente"])
            .reindex(full_index, fill_value=0)
            .reset_index()
        )

        return trend
    
    def _create_line_chart(
        self,
        trend: pd.DataFrame,
        category_col: str,
        category_order: Optional[List[str]] = None,
    ) -> px.line:
        """Create a plotly line chart."""
        category_orders = {category_col: category_order} if category_order else None
        fig = px.line(
            trend,
            x="Periodo",
            y="ID del ticket",
            color=category_col,
            color_discrete_sequence=px.colors.qualitative.Plotly,
            markers=True,
            text="ID del ticket",
            category_orders=category_orders,
            labels={
                "Periodo": "Mes",
                "ID del ticket": "Tickets",
                category_col: category_col,
            },
        )
        fig.update_traces(textposition="top center", texttemplate="%{y}")
        
        tick_vals = sorted(trend["Periodo"].unique())
        tick_text = []
        for val in tick_vals:
            ts = pd.Timestamp(val)
            month_name = self.config.MONTH_NAMES_ES.get(ts.month, "")
            year_suffix = f"{ts.year % 100:02d}"
            tick_text.append(f"{month_name}/{year_suffix}")
        fig.update_layout(
            template="plotly_white",
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(tickmode="array", tickvals=tick_vals, ticktext=tick_text),
        )
        self._apply_readable_chart_layout(fig)
        
        return fig

    def _create_usage_line_chart(self, trend: pd.DataFrame) -> px.line:
        """Create a plotly line chart for logins."""
        fig = px.line(
            trend,
            x="Periodo",
            y="logins",
            color="Cliente",
            color_discrete_sequence=px.colors.qualitative.Plotly,
            markers=True,
            text="logins",
            labels={
                "Periodo": "Mes",
                "logins": "Logins",
                "Cliente": "Cliente",
            },
        )
        fig.update_traces(textposition="top center", texttemplate="%{y}")

        tick_vals = sorted(trend["Periodo"].unique())
        tick_text = []
        for val in tick_vals:
            ts = pd.Timestamp(val)
            month_name = self.config.MONTH_NAMES_ES.get(ts.month, "")
            year_suffix = f"{ts.year % 100:02d}"
            tick_text.append(f"{month_name}/{year_suffix}")
        fig.update_layout(
            template="plotly_white",
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(tickmode="array", tickvals=tick_vals, ticktext=tick_text),
        )
        self._apply_readable_chart_layout(fig)

        return fig

    def _create_flow_line_chart(self, flow: pd.DataFrame) -> px.line:
        """Create a plotly line chart for ticket flow."""
        fig = px.line(
            flow,
            x="Periodo",
            y="Tickets",
            color="Tipo",
            color_discrete_sequence=px.colors.qualitative.Plotly,
            markers=True,
            text="Tickets",
            labels={
                "Periodo": "Mes",
                "Tickets": "Tickets",
                "Tipo": "Flujo",
            },
        )
        fig.update_traces(textposition="top center", texttemplate="%{y}")

        tick_vals = sorted(flow["Periodo"].unique())
        tick_text = []
        for val in tick_vals:
            ts = pd.Timestamp(val)
            month_name = self.config.MONTH_NAMES_ES.get(ts.month, "")
            year_suffix = f"{ts.year % 100:02d}"
            tick_text.append(f"{month_name}/{year_suffix}")
        fig.update_layout(
            template="plotly_white",
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(tickmode="array", tickvals=tick_vals, ticktext=tick_text),
        )
        self._apply_readable_chart_layout(fig)

        return fig

    @staticmethod
    def _apply_readable_chart_layout(fig: px.line) -> None:
        """Apply a consistent and slightly larger typography for chart readability."""
        fig.update_layout(
            font=dict(size=14),
            legend=dict(font=dict(size=15), title=dict(font=dict(size=15))),
            xaxis=dict(title=dict(font=dict(size=16)), tickfont=dict(size=15)),
            yaxis=dict(title=dict(font=dict(size=16)), tickfont=dict(size=15)),
        )
        fig.update_traces(textfont=dict(size=15))
