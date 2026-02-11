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
        title: str,
    ) -> None:
        """Render a monthly trend chart with labels."""
        trend = self._prepare_trend_data(df, category_col, selected_year)
        fig = self._create_line_chart(trend, category_col, title)
        
        st.subheader(title)
        st.plotly_chart(fig, use_container_width=True)
    
    def _prepare_trend_data(
        self, df: pd.DataFrame, category_col: str, selected_year: Optional[int]
    ) -> pd.DataFrame:
        """Prepare trend data for visualization."""
        trend = (
            df.groupby(["Periodo", category_col])["ID del ticket"]
            .nunique()
            .reset_index()
        )
        
        if selected_year is not None:
            all_months = pd.date_range(
                start=f"{int(selected_year)}-01-01",
                end=f"{int(selected_year)}-12-01",
                freq="MS",
            )
        else:
            all_months = pd.to_datetime(sorted(df["Periodo"].dropna().unique()))
        
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
    
    def _create_line_chart(
        self, trend: pd.DataFrame, category_col: str, title: str
    ) -> px.line:
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
                category_col: title.replace("Tendencia de ", "").replace(" por mes", ""),
            },
        )
        fig.update_traces(textposition="top center", texttemplate="%{y}")
        
        tick_vals = sorted(trend["Periodo"].unique())
        tick_text = [
            self.config.MONTH_NAMES_ES.get(pd.Timestamp(val).month, "") for val in tick_vals
        ]
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(tickmode="array", tickvals=tick_vals, ticktext=tick_text),
        )
        
        return fig
