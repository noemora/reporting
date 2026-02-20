"""
Streamlit app for ticket reporting and KPI analysis.

This is the main entry point for the application.
Architecture follows SOLID principles with clear separation of concerns.
"""
import streamlit as st

from config import AppConfig
from data import ExcelDataLoader, DataValidator, DataPreprocessor
from dashboard import DashboardOrchestrator


class TicketAnalysisApp:
    """Main application class that coordinates all components."""
    
    def __init__(self):
        self.config = AppConfig()
        self.data_loader = ExcelDataLoader()
        self.validator = DataValidator(self.config)
        self.preprocessor = DataPreprocessor(self.config)
        self.dashboard = DashboardOrchestrator(self.config)
    
    def run(self) -> None:
        """Run the main application."""
        st.set_page_config(page_title="Informes Gerenciales de Tickets", layout="wide")
        st.title("Informes Gerenciales de Tickets")

        if "processed" not in st.session_state:
            st.session_state.processed = False
        if "uploader_key" not in st.session_state:
            st.session_state.uploader_key = 0

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
                st.caption("Carga el Excel del reporte comercial y el Excel de logins.")
                col1, col2 = st.columns(2)
                with col1:
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

                can_process = report_file is not None and logins_file is not None
                process_clicked = st.button("Procesar informacion", disabled=not can_process)
                if process_clicked:
                    st.session_state.report_bytes = report_file.getvalue()
                    st.session_state.logins_bytes = logins_file.getvalue()
                    st.session_state.processed = True
                    st.rerun()

                if not can_process:
                    st.info("Carga ambos archivos para habilitar el procesamiento.")
                    return

                if not st.session_state.processed:
                    st.info("Haz clic en 'Procesar informacion' para iniciar.")
                    return

        report_bytes = st.session_state.get("report_bytes")
        logins_bytes = st.session_state.get("logins_bytes")
        if not report_bytes or not logins_bytes:
            st.warning("No se encontraron archivos cargados para procesar.")
            return

        usage_df = self.data_loader.load(logins_bytes)

        # Load and process data
        df = self.data_loader.load(report_bytes)
        df = self.validator.validate_and_standardize(df)
        df = self.preprocessor.preprocess(df)
        
        tab_soporte, tab_comercial = st.tabs(["Dashboard Soporte", "Dashboard Comercial"])

        with tab_soporte:
            self.dashboard.render_dashboard(
                df,
                usage_df,
                dashboard_name="Dashboard Soporte",
                widget_prefix="soporte",
            )

        with tab_comercial:
            self.dashboard.render_dashboard(
                df,
                usage_df,
                dashboard_name="Dashboard Comercial",
                widget_prefix="comercial",
            )


def main():
    """Application entry point."""
    app = TicketAnalysisApp()
    app.run()


if __name__ == "__main__":
    main()
