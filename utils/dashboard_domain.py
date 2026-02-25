"""Reglas de dominio reutilizables para KPIs de dashboard."""
from typing import List

import pandas as pd

PRIORITY_LABEL_MAP = {
    "urgente": "Urgente",
    "urgent": "Urgente",
    "alta": "Alta",
    "high": "Alta",
    "media": "Media",
    "medium": "Media",
    "baja": "Baja",
    "low": "Baja",
}

PRIORITY_ORDER_MAP = {
    "urgente": 0,
    "urgent": 0,
    "alta": 1,
    "high": 1,
    "media": 2,
    "medium": 2,
    "baja": 3,
    "low": 3,
}

COMMERCIAL_STATUS_ORDER = ["Pendiente", "En progreso", "Resuelto"]


def normalize_priority_labels(priority_series: pd.Series) -> pd.Series:
    """Normalize priority values to Spanish criticidad labels."""
    priority_norm = priority_series.astype(str).str.strip().str.lower()
    return priority_norm.map(PRIORITY_LABEL_MAP).fillna("Sin criticidad")


def build_priority_category_order(priority_labels: pd.Series) -> List[str]:
    """Build sorted category order for priority labels."""
    labels = priority_labels.astype(str).str.strip()
    sort_values = labels.str.lower().map(PRIORITY_ORDER_MAP).fillna(99)
    return (
        pd.DataFrame(
            {
                "label": labels,
                "sort": sort_values,
                "tie": labels.str.lower(),
            }
        )
        .drop_duplicates(subset=["label"])
        .sort_values(by=["sort", "tie"])["label"]
        .tolist()
    )


def map_priority_sort(priority_labels: pd.Series) -> pd.Series:
    """Return numeric sort series for priority labels."""
    return priority_labels.astype(str).str.strip().str.lower().map(PRIORITY_ORDER_MAP).fillna(99)


def build_commercial_estado(estado_grouped: pd.Series) -> pd.Series:
    """Map grouped status into commercial status buckets."""
    estado_series = estado_grouped.fillna("").astype(str).str.strip().str.lower()
    estado_comercial = pd.Series(pd.NA, index=estado_grouped.index, dtype="object")
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
    return estado_comercial
