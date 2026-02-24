"""Application configuration settings."""
from dataclasses import dataclass
from typing import Dict, List, Set


@dataclass
class AppConfig:
    """Configuration container for application settings."""
    
    REQUIRED_COLUMNS: List[str] = None
    DATETIME_COLUMNS: List[str] = None
    NUMERIC_COLUMNS: List[str] = None
    MONTH_NAMES_ES: Dict[int, str] = None
    RESOLVED_STATES: Set[str] = None
    PROD_ENVIRONMENTS: Set[str] = None
    
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

