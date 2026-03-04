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

## Ejecucion
- `streamlit run app.py`

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

### Nota sobre archivos de datos
- `datasources/` se excluye del contexto de build (`.dockerignore`) para no copiar datos locales al contenedor.
- Si necesitas montar datos locales en runtime, puedes agregar un volumen en `docker-compose.yml`.

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
   - Dashboard Soporte: incluye Usabilidad, Incidencias (Flujo, Cliente, Team Asignado, Criticidad, SLA, SLA por criticidad, Modulo, Ambiente, Estado), Cambios (Cliente, Team, Módulo, Estado) y Mejoras (Team, Módulo, Estado).
   - Dashboard Comercial: incluye Usabilidad, Incidencias (Flujo, Cliente, Criticidad, SLA, SLA por criticidad, Módulo, Estado) y Cambios (Cliente, Módulo, Estado).
4. Selecciona filtros por año, cliente, team asignado y criticidad.
5. Revisa KPIs, tablas y tendencias.

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
- Si agregas KPIs, ajusta dashboard/orchestrator.py y los helpers de services/ y ui/.
- Si actualizas librerias del entorno local, regenera y versiona `requirements.lock.txt` para mantener la reproducibilidad entre equipos.

