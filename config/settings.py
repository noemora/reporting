"""Application configuration settings."""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class AppConfig:
    """Configuration container for application settings."""
    
    REQUIRED_COLUMNS: List[str] = None
    DATETIME_COLUMNS: List[str] = None
    NUMERIC_COLUMNS: List[str] = None
    MONTH_NAMES_ES: Dict[int, str] = None
    RESOLVED_STATES: Set[str] = None
    PROD_ENVIRONMENTS: Set[str] = None
    FRESHDESK_DOMAIN: Optional[str] = None
    FRESHDESK_API_KEY: Optional[str] = None
    FRESHDESK_PER_PAGE: int = 100
    FRESHDESK_TIMEOUT_SECONDS: int = 30
    FRESHDESK_RATE_LIMIT_DELAY_SECONDS: float = 0.6
    FRESHDESK_BACKFILL_UPDATED_SINCE: str = "2000-01-01T00:00:00Z"
    FRESHDESK_OUTPUT_DIR: str = "datasources"
    FRESHDESK_SNAPSHOT_FILENAME: str = "freshdesk_tickets.parquet"
    FRESHDESK_STATE_FILENAME: str = "freshdesk_sync_state.json"
    FRESHDESK_CUSTOM_FIELD_MAPPING: Dict[str, str] = None
    FRESHDESK_STATUS_MAP: Dict[int, str] = None
    FRESHDESK_PRIORITY_MAP: Dict[int, str] = None
    FRESHDESK_SOURCE_MAP: Dict[int, str] = None
    
    def __post_init__(self):
        if self.REQUIRED_COLUMNS is None:
            self.REQUIRED_COLUMNS = [
                "ID del ticket", "Asunto", "Estado", "Prioridad", "Origen", "Tipo",
                "Agente", "Grupo", "Hora de creacion", "Tiempo de vencimiento",
                "Hora de resolucion", "Hora de cierre", "Hora de Ultima actualizacion",
                "Tiempo de respuesta inicial", "Tiempo transcurrido",
                "Tiempo de primera respuesta (en horas)", "Tiempo de resolucion (en horas)",
                "Interacciones del agente", "Interacciones del cliente",
                "Estado de resolucion", "Estado de primera respuesta", "Etiquetas",
                "Resultados de la encuesta", "Habilidad", "Tipo de asociacion",
                "El estado de cada respuesta", "Producto", "Ambiente", "Team Asignado",
                "Responsable Tk", "Url afectada", "Fecha Estimada", "Esfuerzo en Horas",
                "Modulo", "Nombre completo", "ID del contacto",
            ]
        
        if self.DATETIME_COLUMNS is None:
            self.DATETIME_COLUMNS = [
                "Hora de creacion", "Tiempo de vencimiento", "Hora de resolucion",
                "Hora de cierre", "Hora de Ultima actualizacion", "Fecha Estimada",
            ]
        
        if self.NUMERIC_COLUMNS is None:
            self.NUMERIC_COLUMNS = [
                "Tiempo de primera respuesta (en horas)", "Tiempo de resolucion (en horas)",
                "Tiempo de respuesta inicial", "Tiempo transcurrido",
                "Interacciones del agente", "Interacciones del cliente", "Esfuerzo en Horas",
            ]
        
        if self.MONTH_NAMES_ES is None:
            self.MONTH_NAMES_ES = {
                1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
                7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
            }
        
        if self.RESOLVED_STATES is None:
            self.RESOLVED_STATES = {"resuelto", "cerrado", "solucionado", "resueltos", "resolved", "closed"}
        
        if self.PROD_ENVIRONMENTS is None:
            self.PROD_ENVIRONMENTS = {"prod (cliente)", "produccion", "produccion ", "prod"}

        if self.FRESHDESK_CUSTOM_FIELD_MAPPING is None:
            self.FRESHDESK_CUSTOM_FIELD_MAPPING = {
                # Ajusta estos valores segun los nombres reales de custom fields en Freshdesk.
                "Modulo": "cf_modulo",
                "Team Asignado": "cf_team_asignado",
                "Responsable Tk": "cf_responsable_tk",
                "Url afectada": "cf_url_afectada",
                "Fecha Estimada": "cf_fecha_estimada",
                "Esfuerzo en Horas": "cf_esfuerzo_en_horas",
                "Producto": "cf_producto",
                "Ambiente": "cf_ambiente",
                "Habilidad": "cf_habilidad",
            }

        if self.FRESHDESK_STATUS_MAP is None:
            self.FRESHDESK_STATUS_MAP = {
                2: "Abierto",
                3: "Pendiente",
                4: "Resuelto",
                5: "Cerrado",
            }

        if self.FRESHDESK_PRIORITY_MAP is None:
            self.FRESHDESK_PRIORITY_MAP = {
                1: "Baja",
                2: "Media",
                3: "Alta",
                4: "Urgente",
            }

        if self.FRESHDESK_SOURCE_MAP is None:
            self.FRESHDESK_SOURCE_MAP = {
                1: "Email",
                2: "Portal",
                3: "Telefono",
                7: "Chat",
                9: "Feedback Widget",
                10: "Outbound Email",
            }

    @property
    def project_root(self) -> Path:
        """Return absolute project root path."""
        return Path(__file__).resolve().parent.parent

    @property
    def freshdesk_output_path(self) -> Path:
        """Return output directory for Freshdesk sync files."""
        return self.project_root / self.FRESHDESK_OUTPUT_DIR

    @property
    def freshdesk_snapshot_path(self) -> Path:
        """Return snapshot parquet path."""
        return self.freshdesk_output_path / self.FRESHDESK_SNAPSHOT_FILENAME

    @property
    def freshdesk_state_path(self) -> Path:
        """Return sync metadata json path."""
        return self.freshdesk_output_path / self.FRESHDESK_STATE_FILENAME

    @property
    def freshdesk_base_url(self) -> str:
        """Return base URL for Freshdesk API v2."""
        if not self.FRESHDESK_DOMAIN:
            return ""
        domain = self.FRESHDESK_DOMAIN.strip().replace("https://", "").replace("http://", "")
        return f"https://{domain}/api/v2"

