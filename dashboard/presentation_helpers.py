"""Mensajes de presentación reutilizables para dashboards."""

import streamlit as st


def info_no_data_year(year: int) -> None:
    """Render no-data info for a specific year."""
    st.info(f"ℹ️ No hay datos para el año {year}")


def info_no_data_year_with_zeros(year: int) -> None:
    """Render no-data info with explicit zero-value behavior."""
    st.info(f"ℹ️ No hay datos para el año {year}. Se muestran valores en 0.")


def warning_no_data_section(section_label: str) -> None:
    """Render no-data warning for a dashboard section."""
    st.warning(f"No hay datos para {section_label} con los filtros seleccionados.")


def info_no_top_modules_year(year: int) -> None:
    """Render no-data message for top-modules annual view."""
    st.info(f"ℹ️ No hay datos de módulos TOP 5 para el año {year}")


def info_no_valid_priorities_year(year: int) -> None:
    """Render no-data message for invalid priorities in SLA context."""
    st.info(f"ℹ️ No hay criticidades válidas para el año {year}. Se muestran valores en 0.")


def info_no_sla_data_year(year: int) -> None:
    """Render no-data message for missing SLA rows in year."""
    st.info(f"ℹ️ No hay datos de SLA para el año {year}. Se muestran valores en 0.")
