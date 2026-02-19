"""Export utilities for dashboard tables."""
from __future__ import annotations

from io import BytesIO
import re
from typing import Any, List, Optional, Tuple

import pandas as pd


class ExportBuilder:
    """Builds export files (Excel and PDF) from dashboard tables."""

    @staticmethod
    def build_excel_bytes(
        tables: List[Tuple[str, pd.DataFrame]],
        charts: Optional[List[Tuple[str, Any]]] = None,
    ) -> bytes:
        """Build an Excel file with one sheet per table and chart in the same sheet."""
        from openpyxl.drawing.image import Image as XLImage

        output = BytesIO()
        chart_entries = list(charts or [])
        consumed_chart_indexes: set[int] = set()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            used_names = set()
            for raw_name, table in tables:
                if table is None or table.empty:
                    continue
                sheet_name = ExportBuilder._safe_sheet_name(raw_name, used_names)
                used_names.add(sheet_name)
                export_table = table.reset_index().copy()
                export_table.to_excel(writer, sheet_name=sheet_name, index=False)

                ws = writer.book[sheet_name]
                header_row = 1
                data_start_row = 2
                data_end_row = len(export_table) + 1
                start_col = 1
                end_col = export_table.shape[1]
                ExportBuilder._coerce_table_cell_types(
                    ws,
                    data_start_row=data_start_row,
                    data_end_row=data_end_row,
                    start_col=start_col,
                    end_col=end_col,
                )
                ExportBuilder._autofit_columns(
                    ws,
                    start_col=start_col,
                    end_col=end_col,
                    header_row=header_row,
                    data_start_row=data_start_row,
                    data_end_row=data_end_row,
                )

                chart_idx = ExportBuilder._pick_chart_index(raw_name, chart_entries, consumed_chart_indexes)
                if chart_idx is None:
                    continue

                chart_name, chart_fig = chart_entries[chart_idx]
                consumed_chart_indexes.add(chart_idx)
                start_row = len(export_table) + 4
                ws[f"A{start_row}"] = f"Gráfico: {chart_name}"

                image_bytes = ExportBuilder._figure_to_png_bytes(chart_fig)
                if image_bytes is not None:
                    img_stream = BytesIO(image_bytes)
                    image = XLImage(img_stream)
                    image.width = 1100
                    image.height = 400
                    ws.add_image(image, f"A{start_row + 1}")
                    continue

                native_ok = ExportBuilder._add_native_excel_chart(ws, chart_fig, start_row + 1)
                if not native_ok:
                    ws[f"A{start_row + 1}"] = "No se pudo generar este gráfico en Excel."

        output.seek(0)
        return output.getvalue()

    @staticmethod
    def build_pdf_bytes(
        tables: List[Tuple[str, pd.DataFrame]],
        title: str,
        filters_text: str,
        charts: Optional[List[Tuple[str, Any]]] = None,
    ) -> bytes:
        """Build a PDF file with visible tables and optional charts."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Image as RLImage
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        output = BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=landscape(A4),
            leftMargin=10 * mm,
            rightMargin=10 * mm,
            topMargin=10 * mm,
            bottomMargin=10 * mm,
        )
        styles = getSampleStyleSheet()
        story = [
            Paragraph(title, styles["Title"]),
            Spacer(1, 4 * mm),
            Paragraph(filters_text, styles["Normal"]),
            Spacer(1, 5 * mm),
        ]

        for name, table in tables:
            if table is None or table.empty:
                continue
            story.append(Paragraph(name, styles["Heading3"]))

            export_table = table.reset_index().copy()
            export_table = export_table.fillna("").astype(str)
            header = export_table.columns.tolist()
            rows = export_table.values.tolist()
            matrix = [header] + rows

            col_count = max(len(header), 1)
            page_width = landscape(A4)[0] - (20 * mm)
            col_width = page_width / col_count

            pdf_table = Table(matrix, repeatRows=1, colWidths=[col_width] * col_count)
            pdf_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAEAEA")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            story.append(pdf_table)
            story.append(Spacer(1, 5 * mm))

        max_charts_in_pdf = 6
        valid_charts = [(name, fig) for name, fig in (charts or []) if fig is not None][:max_charts_in_pdf]
        if valid_charts:
            story.append(Paragraph("Gráficos", styles["Heading2"]))
            story.append(Spacer(1, 3 * mm))
            for chart_name, chart_fig in valid_charts:
                story.append(Paragraph(chart_name, styles["Heading3"]))
                chart_bytes = ExportBuilder._figure_to_pdf_image_bytes(chart_fig)
                if chart_bytes is None:
                    story.append(Paragraph("No se pudo renderizar este gráfico.", styles["Normal"]))
                    story.append(Spacer(1, 4 * mm))
                    continue

                chart_image = RLImage(BytesIO(chart_bytes), width=240 * mm, height=82 * mm)
                story.append(chart_image)
                story.append(Spacer(1, 5 * mm))

            if charts and len(charts) > max_charts_in_pdf:
                story.append(
                    Paragraph(
                        f"Nota: se incluyeron solo los primeros {max_charts_in_pdf} gráficos para mantener un tamaño estable del PDF.",
                        styles["Normal"],
                    )
                )
                story.append(Spacer(1, 3 * mm))

        doc.build(story)
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def _safe_sheet_name(raw_name: str, used_names: set[str]) -> str:
        """Generate a valid and unique Excel sheet name."""
        invalid = ["[", "]", "*", "?", "/", "\\", ":"]
        clean_name = raw_name
        for token in invalid:
            clean_name = clean_name.replace(token, "-")
        clean_name = clean_name.strip() or "Hoja"
        clean_name = clean_name[:31]

        if clean_name not in used_names:
            return clean_name

        suffix = 1
        while True:
            candidate = f"{clean_name[:28]}-{suffix}"
            if candidate not in used_names:
                return candidate
            suffix += 1

    @staticmethod
    def _figure_to_png_bytes(fig: Any) -> Optional[bytes]:
        """Convert a Plotly figure to PNG bytes for file export."""
        if fig is None:
            return None
        try:
            return fig.to_image(format="png", width=1200, height=420, scale=1)
        except Exception:
            return None

    @staticmethod
    def _figure_to_pdf_image_bytes(fig: Any) -> Optional[bytes]:
        """Convert a Plotly figure to compressed bytes optimized for PDF memory usage."""
        if fig is None:
            return None
        try:
            png_bytes = fig.to_image(format="png", width=900, height=320, scale=1)
        except Exception:
            return None

        try:
            from PIL import Image

            with Image.open(BytesIO(png_bytes)) as image:
                if image.mode in ("RGBA", "P"):
                    image = image.convert("RGB")
                optimized = BytesIO()
                image.save(optimized, format="JPEG", quality=70, optimize=True)
                optimized.seek(0)
                return optimized.getvalue()
        except Exception:
            return png_bytes

    @staticmethod
    def _pick_chart_index(
        table_name: str,
        charts: List[Tuple[str, Any]],
        consumed_indexes: set[int],
    ) -> Optional[int]:
        """Pick the most suitable chart index for a table name."""
        tokens = ExportBuilder._name_tokens(table_name)

        for idx, (chart_name, chart_fig) in enumerate(charts):
            if idx in consumed_indexes or chart_fig is None:
                continue
            chart_tokens = ExportBuilder._name_tokens(chart_name)
            if tokens.intersection(chart_tokens):
                return idx

        for idx, (_, chart_fig) in enumerate(charts):
            if idx not in consumed_indexes and chart_fig is not None:
                return idx
        return None

    @staticmethod
    def _name_tokens(name: str) -> set[str]:
        """Extract normalized tokens from a table or chart name."""
        normalized = str(name).lower()
        replacements = {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
        }
        for source, target in replacements.items():
            normalized = normalized.replace(source, target)

        parts = [part.strip() for part in normalized.replace("(", " ").replace(")", " ").split("-")]
        words = set()
        for part in parts:
            for token in part.split():
                if token:
                    words.add(token)
        return words

    @staticmethod
    def _add_native_excel_chart(ws: Any, fig: Any, start_row: int) -> bool:
        """Create an Excel-native line chart from Plotly data as fallback."""
        try:
            from openpyxl.chart import LineChart, Reference
            from openpyxl.utils import get_column_letter
        except Exception:
            return False

        traces = []
        for trace in getattr(fig, "data", []):
            x_raw = getattr(trace, "x", None)
            y_raw = getattr(trace, "y", None)
            x_values = list(x_raw) if x_raw is not None else []
            y_values = list(y_raw) if y_raw is not None else []
            if not x_values or not y_values:
                continue
            name = getattr(trace, "name", None) or f"Serie {len(traces) + 1}"
            traces.append((name, x_values, y_values))

        if not traces:
            return False

        source_start_col = 200
        source_end_col = source_start_col + len(traces)

        max_len = max(len(y_values) for _, _, y_values in traces)
        ws.cell(row=start_row, column=source_start_col, value="Periodo")
        for col_idx, (name, _, _) in enumerate(traces, start=source_start_col + 1):
            ws.cell(row=start_row, column=col_idx, value=str(name))

        base_x = traces[0][1]
        for row_offset in range(max_len):
            row_number = start_row + 1 + row_offset
            x_value = base_x[row_offset] if row_offset < len(base_x) else ""
            ws.cell(row=row_number, column=source_start_col, value=str(x_value))

            for col_idx, (_, _, y_values) in enumerate(traces, start=source_start_col + 1):
                value = y_values[row_offset] if row_offset < len(y_values) else None
                try:
                    numeric_value = float(value) if value is not None else None
                except (TypeError, ValueError):
                    numeric_value = None
                ws.cell(row=row_number, column=col_idx, value=numeric_value)

        for hidden_col in range(source_start_col, source_end_col + 1):
            ws.column_dimensions[get_column_letter(hidden_col)].hidden = True

        chart = LineChart()
        chart.title = "Tendencia"
        chart.height = 8
        chart.width = 22
        chart.plotVisOnly = False
        data_ref = Reference(
            ws,
            min_col=source_start_col + 1,
            min_row=start_row,
            max_col=source_end_col,
            max_row=start_row + max_len,
        )
        cats_ref = Reference(
            ws,
            min_col=source_start_col,
            min_row=start_row + 1,
            max_row=start_row + max_len,
        )
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        ws.add_chart(chart, f"A{start_row}")
        return True

    @staticmethod
    def _coerce_table_cell_types(
        ws: Any,
        data_start_row: int,
        data_end_row: int,
        start_col: int,
        end_col: int,
    ) -> None:
        """Convert text-like numeric cells into Excel numeric types and formats."""
        for row in ws.iter_rows(
            min_row=data_start_row,
            max_row=data_end_row,
            min_col=start_col,
            max_col=end_col,
        ):
            for cell in row:
                if not isinstance(cell.value, str):
                    continue
                parsed = ExportBuilder._parse_numeric_text(cell.value)
                if parsed is None:
                    continue
                value, number_format = parsed
                cell.value = value
                if number_format:
                    cell.number_format = number_format

    @staticmethod
    def _parse_numeric_text(value: str) -> Optional[Tuple[float | int, str]]:
        """Parse string values to int/float/percent preserving expected formatting."""
        text = str(value).strip()
        if not text:
            return None

        percent_match = re.fullmatch(r"-?\d+(?:[\.,]\d+)?%", text)
        if percent_match:
            numeric_text = text[:-1].replace(".", "").replace(",", ".")
            try:
                percent_value = float(numeric_text) / 100
                return percent_value, "0.0%"
            except ValueError:
                return None

        if re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", text):
            try:
                return int(text.replace(".", "")), "#,##0"
            except ValueError:
                return None

        if re.fullmatch(r"-?\d+", text):
            try:
                return int(text), "#,##0"
            except ValueError:
                return None

        if re.fullmatch(r"-?\d+[\.,]\d+", text):
            normalized = text.replace(",", ".")
            try:
                decimals = len(normalized.split(".")[-1])
                number_format = "#,##0." + ("0" * min(decimals, 4))
                return float(normalized), number_format
            except ValueError:
                return None

        return None

    @staticmethod
    def _autofit_columns(
        ws: Any,
        start_col: int,
        end_col: int,
        header_row: int,
        data_start_row: int,
        data_end_row: int,
    ) -> None:
        """Set column widths based on content length for header and table rows."""
        from openpyxl.utils import get_column_letter

        for col_idx in range(start_col, end_col + 1):
            max_length = 0
            header_value = ws.cell(row=header_row, column=col_idx).value
            if header_value is not None:
                max_length = max(max_length, len(str(header_value)))

            for row_idx in range(data_start_row, data_end_row + 1):
                cell_value = ws.cell(row=row_idx, column=col_idx).value
                if cell_value is None:
                    continue
                if isinstance(cell_value, (int, float)):
                    text_len = len(f"{cell_value:,.2f}")
                else:
                    text_len = len(str(cell_value))
                max_length = max(max_length, text_len)

            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = min(max(max_length + 2, 10), 40)
