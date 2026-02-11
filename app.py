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
        st.caption("Carga un Excel, filtra y analiza KPIs de tickets.")
        
        uploaded_file = st.file_uploader(
            "Carga el archivo Excel", type=["xlsx"], accept_multiple_files=False
        )
        
        if not uploaded_file:
            st.info("Carga un archivo Excel para iniciar el análisis.")
            return
        
        # Load and process data
        df = self.data_loader.load(uploaded_file.getvalue())
        df = self.validator.validate_and_standardize(df)
        df = self.preprocessor.preprocess(df)
        
        # Render dashboard
        self.dashboard.render_dashboard(df)


def main():
    """Application entry point."""
    app = TicketAnalysisApp()
    app.run()


if __name__ == "__main__":
    main()
