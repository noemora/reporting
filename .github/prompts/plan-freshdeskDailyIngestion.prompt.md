## Plan: Ingesta Freshdesk automatica diaria

Crear una fuente de datos Freshdesk desacoplada del flujo de UI actual, con carga historica inicial + sincronizacion incremental diaria a las 12:00 UTC, guardando en Parquet local y reutilizando `validator`/`preprocessor` para no romper arquitectura SRP/OCP.

**Steps**
1. Fase 1 - Fundacion de ingestion: crear modulo Freshdesk en `datasources/` para autenticacion, paginacion y parseo a DataFrame.
2. Fase 1 - Configuracion central: extender `config/settings.py` con parametros Freshdesk, limites, ruta de salida y mapeos de columnas.
3. Fase 1 - Contrato de origen de datos: introducir interfaz/factory para seleccionar `excel` o `freshdesk`, manteniendo `app.py` liviano y `dashboard/orchestrator.py` solo como coordinador.
4. Fase 2 - ETL incremental y persistencia: crear servicio de sync con `backfill` inicial completo + `incremental` diario por `updated_since`, deduplicacion por `ID del ticket`, y watermark de ultima corrida.
5. Fase 2 - Mapeo tickets-only: mapear columnas estandar/custom disponibles en `tickets` hacia `REQUIRED_COLUMNS`; definir politica explicita para columnas no disponibles en fase 1 (`null/default`).
6. Fase 3 - Integracion Streamlit: priorizar lectura del Parquet mas reciente cuando exista, con fallback a carga manual Excel.
7. Fase 3 - Scheduler multi-entorno: exponer un comando CLI unico de sync usable tanto en Windows Task Scheduler como en cron Linux/docker, con horario fijo 12:00 UTC.
8. Fase 4 - Operacion/documentacion: actualizar `README.md` con `.env`, ejecucion manual, backfill, incremental, scheduler Windows/Linux y troubleshooting.

**Relevant files**
- `c:\Users\NoeSaulMoraHerrera\Repos\KPI\app.py` - mantener pipeline `load -> validate_and_standardize -> preprocess` y agregar seleccion de fuente sin logica pesada.
- `c:\Users\NoeSaulMoraHerrera\Repos\KPI\config\settings.py` - nueva configuracion Freshdesk y mapeos.
- `c:\Users\NoeSaulMoraHerrera\Repos\KPI\data\loader.py` - evolucionar a factory/orquestador de fuentes.
- `c:\Users\NoeSaulMoraHerrera\Repos\KPI\data\validator.py` - validar contrato de columnas requerido.
- `c:\Users\NoeSaulMoraHerrera\Repos\KPI\data\preprocessor.py` - reutilizar parseo de fechas/numericos.
- `c:\Users\NoeSaulMoraHerrera\Repos\KPI\datasources\` - nueva implementacion Freshdesk.
- `c:\Users\NoeSaulMoraHerrera\Repos\KPI\docker-compose.yml` - opcional para scheduler en contenedor Linux.
- `c:\Users\NoeSaulMoraHerrera\Repos\KPI\README.md` - documentacion de operacion diaria.

**Verification**
1. Probar conectividad API con `.env` y paginacion real.
2. Ejecutar backfill inicial y confirmar volumen esperado (>8000) y tiempos.
3. Ejecutar incremental con `updated_since` y validar deduplicacion por `ID del ticket`.
4. Verificar esquema final contra `REQUIRED_COLUMNS`, `DATETIME_COLUMNS` y `NUMERIC_COLUMNS`.
5. Levantar Streamlit y confirmar lectura automatica de Parquet + fallback manual.
6. Probar scheduler en Windows y Linux con el mismo comando CLI y logs.
7. Correr chequeo de errores/smoke test de dashboard para descartar regresiones.

**Decisions capturadas**
- Auth: API Key via `.env`.
- Frecuencia: diario 12:00 UTC.
- Estrategia: backfill inicial + incremental diario.
- Persistencia: archivo local Parquet en `datasources/`.
- Scheduler: multi-entorno (Windows local + Linux/docker).
- Alcance fase 1: solo `tickets` (sin enriquecimiento de `contacts/agents/satisfaccion`).

Plan guardado en `/memories/session/plan.md`. Si lo apruebas, queda listo para handoff e implementacion.
