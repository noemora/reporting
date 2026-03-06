"""
Streamlit app for ticket reporting and KPI analysis.

This is the main entry point for the application.
Architecture follows SOLID principles with clear separation of concerns.
"""
import streamlit as st
from pathlib import Path

from config import AppConfig
from data import ExcelDataLoader, FreshdeskSnapshotLoader, DataValidator, DataPreprocessor
from dashboard import DashboardOrchestrator


class TicketAnalysisApp:
    """Main application class that coordinates all components."""
    
    def __init__(self):
        self.config = AppConfig()
        self.data_loader = ExcelDataLoader()
        self.snapshot_loader = FreshdeskSnapshotLoader()
        self.validator = DataValidator(self.config)
        self.preprocessor = DataPreprocessor(self.config)
        self.dashboard = DashboardOrchestrator(self.config)

    def _get_report_df_from_source(self) -> tuple:
        """Resolve report DataFrame from selected source in session state."""
        source = st.session_state.get("report_source", "manual")

        if source == "freshdesk":
            snapshot_path = self.config.freshdesk_snapshot_path
            if not snapshot_path.exists():
                raise FileNotFoundError("No existe snapshot Freshdesk para cargar.")
            snapshot_signature = snapshot_path.stat().st_mtime
            return self.snapshot_loader.load(str(snapshot_path), snapshot_signature), "snapshot"

        report_bytes = st.session_state.get("report_bytes")
        if not report_bytes:
            raise ValueError("No se encontro archivo manual del reporte comercial.")
        return self.data_loader.load(report_bytes), "manual"

    @staticmethod
    def _apply_readability_styles() -> None:
        """Apply global UI styles to improve readability."""
        st.markdown(
            """
            <style>
                section.main table {
                    font-size: 2rem !important;
                }

                section.main table th {
                    font-size: 4rem !important;
                }

                section.main table td {
                    font-size: 2rem !important;
                }

                [data-testid="stTable"] table,
                .stTable table,
                [data-testid="stDataFrame"] table,
                .stDataFrame table {
                    font-size: 2rem !important;
                }

                [data-testid="stTable"] table th,
                .stTable table th,
                [data-testid="stDataFrame"] table th,
                .stDataFrame table th,
                [data-testid="stTable"] [role="columnheader"],
                [data-testid="stDataFrame"] [role="columnheader"] {
                    font-size: 4rem !important;
                }

                [data-testid="stTable"] table td,
                .stTable table td,
                [data-testid="stDataFrame"] table td,
                .stDataFrame table td,
                [data-testid="stTable"] [role="cell"],
                [data-testid="stDataFrame"] [role="cell"] {
                    font-size: 2rem !important;
                }

                [data-testid="stTable"] *,
                [data-testid="stDataFrame"] * {
                    line-height: 1.2 !important;
                }

                [data-testid="stTabs"] [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
                    font-size: 1.4rem !important;
                    font-weight: 600 !important;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

    @staticmethod
    def _render_navbar_logo() -> None:
        """Render app logo in navbar (left side) when available."""
        logo_path = Path(__file__).resolve().parent / "assets" / "marca-flat.png"
        if logo_path.exists() and hasattr(st, "logo"):
            st.logo(str(logo_path))
    
    def run(self) -> None:
        """Run the main application."""
        logo_path = Path(__file__).resolve().parent / "assets" / "marca-flat.png"
        page_icon = str(logo_path) if logo_path.exists() else None
        st.set_page_config(
            page_title="Informes Gerenciales de Tickets",
            page_icon=page_icon,
            layout="wide",
        )
        self._render_navbar_logo()
        self._apply_readability_styles()
        st.title("Informes Gerenciales de Tickets")

        if "processed" not in st.session_state:
            st.session_state.processed = False
        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0
        if "report_source" not in st.session_state:
            st.session_state.report_source = "freshdesk" if self.config.freshdesk_snapshot_path.exists() else "manual"

        with st.expander("Carga de archivos", expanded=not st.session_state.processed):
            if st.session_state.processed:
                st.success("Archivos procesados.")
                if st.button("Cambiar archivos"):
                    st.session_state.processed = False
                    st.session_state.uploader_key += 1
                    st.session_state.pop("report_bytes", None)
                    st.session_state.pop("logins_bytes", None)
                    st.rerun()
            else:
                st.caption("Selecciona fuente para reporte comercial y carga el Excel de logins.")
                source_label = st.radio(
                    "Fuente de datos del reporte comercial",
                    options=["Freshdesk sincronizado", "Archivo manual"],
                    index=0 if st.session_state.report_source == "freshdesk" else 1,
                    key=f"report_source_radio_{st.session_state.uploader_key}",
                )

                selected_source = "freshdesk" if source_label == "Freshdesk sincronizado" else "manual"
                st.session_state.report_source = selected_source

                has_snapshot = self.config.freshdesk_snapshot_path.exists()
                if selected_source == "freshdesk":
                    if has_snapshot:
                        st.success(f"Snapshot detectado: {self.config.freshdesk_snapshot_path}")
                    else:
                        st.warning(
                            "No existe snapshot Freshdesk aun. Ejecuta primero el comando de sync diario."
                        )

                col1, col2 = st.columns(2)
                with col1:
                    report_file = None
                    if selected_source == "manual":
                        report_file = st.file_uploader(
                            "Reporte comercial (Excel)",
                            type=["xlsx", "xls", "csv"],
                            accept_multiple_files=False,
                            key=f"report_file_{st.session_state.uploader_key}",
                        )
                with col2:
                    logins_file = st.file_uploader(
                        "Logins (Excel)",
                        type=["xlsx", "xls", "csv"],
                        accept_multiple_files=False,
                        key=f"logins_file_{st.session_state.uploader_key}",
                    )

                manual_ready = report_file is not None if selected_source == "manual" else has_snapshot
                can_process = manual_ready and logins_file is not None
                process_clicked = st.button("Procesar informacion", disabled=not can_process)
                if process_clicked:
                    if selected_source == "manual" and report_file is not None:
                        st.session_state.report_bytes = report_file.getvalue()
                    else:
                        st.session_state.pop("report_bytes", None)
                    st.session_state.logins_bytes = logins_file.getvalue()
                    st.session_state.processed = True
                    st.rerun()

                if not can_process:
                    if selected_source == "manual":
                        st.info("Carga el reporte comercial y logins para habilitar el procesamiento.")
                    else:
                        st.info("Necesitas snapshot Freshdesk + archivo de logins para procesar.")
                    return

                if not st.session_state.processed:
                    st.info("Haz clic en 'Procesar informacion' para iniciar.")
                    return

        logins_bytes = st.session_state.get("logins_bytes")
        if not logins_bytes:
            st.warning("No se encontraron archivos cargados para procesar.")
            return

        usage_df = self.data_loader.load(logins_bytes)

        try:
            df, source_kind = self._get_report_df_from_source()
        except (FileNotFoundError, ValueError) as error:
            st.error(str(error))
            return

        if source_kind == "snapshot":
            st.caption("Fuente reporte comercial: Freshdesk sincronizado")

        df = self.validator.validate_and_standardize(df)
        df = self.preprocessor.preprocess(df)
        
        tab_soporte, tab_comercial = st.tabs(["Area Soporte", "Area Comercial"])

        with tab_soporte:
            self.dashboard.render_dashboard(
                df,
                usage_df,
                dashboard_name="Reporte - Area Soporte",
                widget_prefix="soporte",
            )

        with tab_comercial:
            self.dashboard.render_dashboard(
                df,
                usage_df,
                dashboard_name="Reporte - Area Comercial",
                widget_prefix="comercial",
            )


def main():
    """Application entry point."""
    app = TicketAnalysisApp()
    app.run()


if __name__ == "__main__":
    main()
