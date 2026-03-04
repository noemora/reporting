"""Cache layer for export artifacts."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

import pandas as pd
import streamlit as st

from services import ExportBuilder


@st.cache_data(show_spinner=False, ttl=3600, max_entries=128)
def build_excel_bytes_cached(
    signature: str,
    _tables: List[Tuple[str, pd.DataFrame]],
    _charts: Optional[List[Tuple[str, Any]]],
) -> bytes:
    """Build/cached Excel bytes using signature as cache key."""
    _ = signature
    return ExportBuilder.build_excel_bytes(_tables, charts=_charts)


@st.cache_data(show_spinner=False, ttl=3600, max_entries=128)
def build_pdf_bytes_cached(
    signature: str,
    title: str,
    filters_text: str,
    _tables: List[Tuple[str, pd.DataFrame]],
    _charts: Optional[List[Tuple[str, Any]]],
) -> bytes:
    """Build/cached PDF bytes using signature as cache key."""
    _ = signature
    return ExportBuilder.build_pdf_bytes(
        _tables,
        title=title,
        filters_text=filters_text,
        charts=_charts,
    )
