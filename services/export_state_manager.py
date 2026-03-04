"""Estado y firma de exportaciones para el dashboard."""
import hashlib
from typing import Dict, List, Optional, Tuple

import pandas as pd

from utils import TextNormalizer


class ExportStateManager:
    """Gestiona cache, firmas y metadatos de exportación."""

    @staticmethod
    def build_filter_labels(
        selected_year: Optional[int],
        selected_client: List[str],
        selected_team: List[str],
        selected_criticidad: List[str],
    ) -> Dict[str, str]:
        """Build display labels for selected filters."""
        return {
            "year": str(int(selected_year)) if selected_year is not None else "Todos",
            "client": ", ".join(selected_client) if selected_client else "Todos",
            "team": ", ".join(selected_team) if selected_team else "Todos",
            "criticidad": ", ".join(selected_criticidad) if selected_criticidad else "Todas",
        }

    @staticmethod
    def build_filters_text(dashboard_name: str, labels: Dict[str, str]) -> str:
        """Build filters summary text for exports."""
        return (
            f"Dashboard: {dashboard_name} | Año: {labels['year']} | Cliente: {labels['client']} | "
            f"Team Asignado: {labels['team']} | Criticidad: {labels['criticidad']}"
        )

    @staticmethod
    def ensure_cache(cache: Dict) -> None:
        """Ensure required export cache keys exist."""
        cache.setdefault("busy", False)
        cache.setdefault("pending_action", None)

    @staticmethod
    def build_signatures(
        export_tables: List[Tuple[str, pd.DataFrame]],
        chart_payload: Optional[List[Tuple[str, object]]],
        labels: Dict[str, str],
    ) -> Tuple[str, str]:
        """Build excel/pdf signatures from current export context."""
        include_charts = chart_payload is not None
        signature_parts = [
            labels["year"],
            labels["client"],
            labels["team"],
            labels["criticidad"],
            str(len(export_tables)),
            f"include_charts={int(include_charts)}",
        ]

        for table_name, table in export_tables:
            table_hash = ExportStateManager._hash_table(table)
            signature_parts.append(f"{table_name}|rows={table.shape[0]}|cols={table.shape[1]}|hash={table_hash}")

        if include_charts and chart_payload:
            signature_parts.append(f"charts_count={len(chart_payload)}")
            for chart_name, chart_fig in chart_payload:
                chart_hash = ExportStateManager._hash_chart(chart_fig)
                signature_parts.append(f"chart={chart_name}|hash={chart_hash}")

        export_signature = "||".join(str(part) for part in signature_parts)
        excel_signature = f"{export_signature}||format=excel||v=3"
        pdf_signature = f"{export_signature}||format=pdf||v=3"
        return excel_signature, pdf_signature

    @staticmethod
    def _hash_table(table: pd.DataFrame) -> str:
        """Build deterministic hash for a dataframe content/shape/order."""
        try:
            row_hashes = pd.util.hash_pandas_object(table, index=True).values.tobytes()
            metadata = "|".join(
                [
                    ";".join(str(col) for col in table.columns.tolist()),
                    ";".join(str(dtype) for dtype in table.dtypes.tolist()),
                    str(table.shape),
                ]
            )
            digest = hashlib.sha1()
            digest.update(metadata.encode("utf-8"))
            digest.update(row_hashes)
            return digest.hexdigest()[:16]
        except Exception:
            fallback = f"{table.shape[0]}|{table.shape[1]}"
            return hashlib.sha1(fallback.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _hash_chart(chart_fig: object) -> str:
        """Build deterministic hash for plotly chart payload."""
        if chart_fig is None:
            return "none"
        try:
            chart_json = chart_fig.to_json()
            return hashlib.sha1(chart_json.encode("utf-8")).hexdigest()[:16]
        except Exception:
            return "invalid"

    @staticmethod
    def reset_cache_if_signature_changed(
        cache: Dict,
        excel_signature: str,
        pdf_signature: str,
    ) -> None:
        """Invalidate cached bytes when signatures changed."""
        if cache.get("excel_signature") != excel_signature:
            cache["excel_signature"] = excel_signature
            cache["excel_bytes"] = None

        if cache.get("pdf_signature") != pdf_signature:
            cache["pdf_signature"] = pdf_signature
            cache["pdf_bytes"] = None

    @staticmethod
    def build_filename_base(
        dashboard_name: str,
        selected_client: List[str],
        year_label: str,
    ) -> str:
        """Build safe base filename for exports."""
        client_token = ",".join(selected_client) if selected_client else "todos"
        safe_client = TextNormalizer.normalize_column_name(client_token).replace(" ", "_")
        safe_year = year_label.replace(" ", "_")
        safe_dashboard = TextNormalizer.normalize_column_name(dashboard_name).replace(" ", "_")
        return f"reporte_filtrado_{safe_dashboard}_{safe_client}_{safe_year}"

    @staticmethod
    def is_excel_ready(cache: Dict, excel_signature: str) -> bool:
        """Return True when excel file is already prepared and valid."""
        return (
            cache.get("excel_bytes") is not None
            and cache.get("excel_signature") == excel_signature
        )

    @staticmethod
    def is_pdf_ready(cache: Dict, pdf_signature: str) -> bool:
        """Return True when pdf file is already prepared and valid."""
        return (
            cache.get("pdf_bytes") is not None
            and cache.get("pdf_signature") == pdf_signature
        )
