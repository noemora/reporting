# Sistema de Informes Gerenciales de Tickets

Aplicacion en Streamlit para cargar el reporte comercial y un archivo de logins, aplicar filtros y mostrar KPIs, tablas y tendencias.

## Requisitos
- Python 3.9+

## Instalacion
1. Crear y activar un entorno virtual.
2. Instalar dependencias:
   - `pip install -r requirements.txt`

## Ejecucion
- `streamlit run app.py`

## Archivos de entrada
### Reporte comercial
Se espera un Excel con las columnas (los nombres se normalizan automaticamente):

- ID del ticket, Asunto, Estado, Prioridad, Origen, Tipo
- Agente, Grupo, Hora de creacion, Tiempo de vencimiento
- Hora de resolucion, Hora de cierre, Hora de Ultima actualizacion
- Tiempo de respuesta inicial, Tiempo transcurrido
- Tiempo de primera respuesta (en horas), Tiempo de resolucion (en horas)
- Interacciones del agente, Interacciones del cliente
- Estado de resolucion, Estado de primera respuesta, Etiquetas
- Resultados de la encuesta, Habilidad, Tipo de asociacion
- El estado de cada respuesta, Producto, Ambiente
- Team Asignado, Responsable Tk, Url afectada, Fecha Estimada
- Esfuerzo en Horas, Modulo, Nombre completo, ID del contacto

Columnas clave para calculos: ID del ticket, Estado, Hora de creacion, Estado de resolucion, Modulo, Ambiente, Grupo, Tipo.

### Logins
Se espera un Excel con columnas (insensible a mayusculas/espacios):

- cliente
- logins
- mes
- año

## Uso
1. Ejecuta la app.
2. Carga ambos archivos.
3. Elige el dashboard:
   - Dashboard Soporte: incluye todas las secciones actuales.
   - Dashboard Comercial: incluye Usabilidad, Incidencias (Flujo, SLA, Módulo, Estado) y Cambios (Team, Módulo, Estado).
4. Selecciona filtros por año, cliente, team asignado y criticidad.
5. Revisa KPIs, tablas y tendencias.

## Estructura del proyecto
- app.py: punto de entrada y coordinacion de componentes.
- config/: configuracion central (columnas requeridas, meses, estados resueltos).
- data/: carga, validacion, normalizacion, preprocesamiento y filtros.
- dashboard/: orquestacion de secciones y KPIs.
- services/: builders para tablas y calculos de apoyo.
- ui/: render de graficos y componentes de interfaz.
- utils/: utilidades de normalizacion de texto.

## Configuracion
- Actualiza los catalogos en config/settings.py para columnas, meses, estados resueltos y ambientes productivos.
- Si agregas KPIs, ajusta dashboard/orchestrator.py y los helpers de services/ y ui/.

