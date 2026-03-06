# Sistema de Informes Gerenciales de Tickets

Aplicacion en Streamlit para reporte gerenciales, en el que se puede aplicar filtros y mostrar KPIs, tablas y tendencias.

## Requisitos
- Python 3.11.9

## Instalacion local
1. Crear y activar un entorno virtual.
   - `python -m venv .venv` o
   - `py -m venv .venv`
2. Instalar dependencias:
   - `pip install -r requirements.txt`
   - Nota: `requirements.txt` referencia `requirements.lock.txt` para mantener versiones fijas y reproducibles (local, Docker y Streamlit Cloud).

## Ejecucion
- `streamlit run app.py`

## Ingestion automatica desde Freshdesk
La app soporta dos fuentes para el reporte comercial:
- `Freshdesk sincronizado` (snapshot local en Parquet).
- `Archivo manual` (Excel cargado desde UI).

### Configuracion
1. Copia `.env.example` a `.env`.
2. Define:
    - `FRESHDESK_DOMAIN` (por ejemplo `empresa.freshdesk.com`).
    - `FRESHDESK_API_KEY`.
   - Opcional: `FRESHDESK_BACKFILL_UPDATED_SINCE` (por ejemplo `2020-01-01T00:00:00Z`).

### Comando unico de sincronizacion
- Backfill inicial completo:
   - `python -m scripts.freshdesk_sync --mode backfill`
- Incremental diario:
   - `python -m scripts.freshdesk_sync --mode incremental`

El comando genera:
- Snapshot: `datasources/freshdesk_tickets.parquet`
- Estado/watermark: `datasources/freshdesk_sync_state.json`

### Scheduler recomendado para Streamlit Community Cloud (GitHub Actions)
Para mantener actualizada la data en Streamlit Community Cloud, usa el workflow versionado en:
- `.github/workflows/freshdesk_daily_sync.yml`

El workflow:
- Corre diario a las `12:00 UTC`.
- Ejecuta `python -m scripts.freshdesk_sync --mode incremental`.
- Guarda cambios en:
   - `datasources/freshdesk_tickets.parquet`
   - `datasources/freshdesk_sync_state.json`
- Hace commit/push automatico al repositorio.

Configuracion requerida en GitHub (`Settings` -> `Secrets and variables` -> `Actions`):
- `FRESHDESK_DOMAIN`
- `FRESHDESK_API_KEY`

Opcional:
- Ejecutar manualmente desde `Actions` -> `Freshdesk Daily Sync` -> `Run workflow`.
- En ejecucion manual puedes elegir:
   - `sync_mode = incremental` (default)
   - `sync_mode = backfill`
- Si eliges `backfill`, puedes indicar `backfill_updated_since` (ejemplo `2020-01-01T00:00:00Z`).
- Si no indicas `backfill_updated_since`, se usa el valor por defecto de la app (`FRESHDESK_BACKFILL_UPDATED_SINCE`).

## Docker (entorno reproducible)
Se incluye una imagen Docker basada en Python `3.11.9` con dependencias bloqueadas en `requirements.lock.txt`.

### Levantar la app
1. Construir y levantar:
   - `docker compose up --build -d`
2. Abrir en navegador:
   - `http://localhost:8501`

### Ver logs
- `docker compose logs -f`

### Detener
- `docker compose down`

### Rebuild forzado (si cambian dependencias)
- `docker compose build --no-cache`
- `docker compose up -d`

## Archivos de entrada
### Reporte comercial
Si usas carga manual, se espera un Excel con las columnas (los nombres se normalizan automaticamente):

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
2. En `Carga de archivos`, selecciona la fuente del reporte comercial:
   - `Freshdesk sincronizado` (usa snapshot local).
   - `Archivo manual` (sube el Excel).
3. Carga el archivo de logins.
4. Procesa informacion.
5. Elige el dashboard:
   - Dashboard Soporte: incluye Usabilidad, Incidencias (Flujo, Cliente, Team Asignado, Criticidad, SLA, SLA por criticidad, Modulo, Ambiente, Estado), Cambios (Cliente, Team, Módulo, Estado) y Mejoras (Team, Módulo, Estado).
   - Dashboard Comercial: incluye Usabilidad, Incidencias (Flujo, Cliente, Criticidad, SLA, SLA por criticidad, Módulo, Estado) y Cambios (Cliente, Módulo, Estado).
6. Selecciona filtros por año, cliente, team asignado y criticidad.
7. Revisa KPIs, tablas y tendencias.

## Estructura del proyecto
- app.py: punto de entrada y coordinacion de componentes.
- config/: configuracion central (columnas requeridas, meses, estados resueltos).
- data/: carga, validacion, normalizacion, preprocesamiento y filtros.
- dashboard/: orquestacion y renderizado modular de secciones y KPIs.
   - orchestrator.py: coordinacion del flujo (filtros, secciones, exportacion).
   - usage_renderer.py: render de usabilidad (logins).
   - sections_renderer.py: fachada de secciones KPI.
   - distribution_renderer.py: KPIs de distribución (flujo, team, cliente, criticidad, módulo, ambiente).
   - status_renderer.py: KPIs de estado.
   - sla_renderer.py: KPIs de SLA y SLA por criticidad.
   - section_renderer_base.py: helpers compartidos de runtime para renderers.
- services/: builders para tablas y calculos de apoyo.
   - export_state_manager.py: estado/cache/firma de exportaciones.
- ui/: render de graficos y componentes de interfaz.
- utils/: utilidades de normalizacion de texto.

## Configuracion
- Actualiza los catalogos en config/settings.py para columnas, meses, estados resueltos y ambientes productivos.
- Si cambian campos custom de Freshdesk, ajusta `FRESHDESK_CUSTOM_FIELD_MAPPING` en `config/settings.py`.
- Si agregas KPIs, ajusta dashboard/orchestrator.py y los helpers de services/ y ui/.
- Si actualizas librerias del entorno local, regenera y versiona `requirements.lock.txt` para mantener la reproducibilidad entre equipos.

