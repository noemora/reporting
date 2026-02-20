"""Chart rendering functionality."""
from typing import Optional
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
    ) -> px.line:
        """Render a monthly trend chart with labels."""
        trend = self._prepare_trend_data(df, category_col, selected_year)
        fig = self._create_line_chart(trend, category_col)
        
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
        self, df: pd.DataFrame, category_col: str, selected_year: Optional[int]
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
                elif str_value == "within sla":
                    return "Cumplido"
                elif str_value == "sla violated":
                    return "Incumplido"
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
        
        all_categories = sorted(df[category_col].dropna().unique())
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
    
    def _create_line_chart(self, trend: pd.DataFrame, category_col: str) -> px.line:
        """Create a plotly line chart."""
        fig = px.line(
            trend,
            x="Periodo",
            y="ID del ticket",
            color=category_col,
            markers=True,
            text="ID del ticket",
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
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(tickmode="array", tickvals=tick_vals, ticktext=tick_text),
        )
        
        return fig

    def _create_usage_line_chart(self, trend: pd.DataFrame) -> px.line:
        """Create a plotly line chart for logins."""
        fig = px.line(
            trend,
            x="Periodo",
            y="logins",
            color="Cliente",
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
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(tickmode="array", tickvals=tick_vals, ticktext=tick_text),
        )

        return fig

    def _create_flow_line_chart(self, flow: pd.DataFrame) -> px.line:
        """Create a plotly line chart for ticket flow."""
        fig = px.line(
            flow,
            x="Periodo",
            y="Tickets",
            color="Tipo",
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
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(tickmode="array", tickvals=tick_vals, ticktext=tick_text),
        )

        return fig
