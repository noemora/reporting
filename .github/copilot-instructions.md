<!-- Instrucciones especificas para este workspace -->

- Proyecto: app de Streamlit para analisis de tickets y usabilidad (reporte comercial + logins).
- Arquitectura: app.py coordina el flujo -> data (carga/validacion/preproceso) -> dashboard (orquesta secciones) -> services/ui (tablas y graficos).
- Todo desarrollo debe regirse por principios SOLID.
- Mantener la separacion de responsabilidades: nada de logica pesada en app.py.
- Nuevas columnas o cambios de nombres: ajustar config/settings.py y, si aplica, data/validator.py.
- Nuevos KPIs o secciones: NO concentrar implementacion en dashboard/orchestrator.py.
- Para nuevas secciones, crear/usar modulos dedicados en dashboard/ (por ejemplo renderers por dominio) y mantener orchestrator solo como coordinador de flujo.
- Regla de responsabilidad unica (SRP): cada archivo/clase debe tener una sola razon de cambio clara (filtros, normalizacion, render de secciones, exportacion, etc.).
- Regla de extension (OCP): agregar funcionalidad mediante nuevas clases/modulos y composicion, evitando modificar grandes bloques existentes cuando no sea necesario.
- Evitar archivos monoliticos: si un archivo supera aprox. 400-500 lineas o mezcla multiples dominios, dividirlo en componentes cohesionados.
- Dependencias internas: preferir inyeccion de dependencias y colaboracion entre clases sobre logica acoplada en una sola clase.
- UI en espanol, textos coherentes con el contexto del negocio.
- En Streamlit, cuando se creen elementos repetidos (especialmente en tabs, columnas o vistas paralelas), asignar key unicas y estables para evitar StreamlitDuplicateElementId.
- Prefiere operaciones vectorizadas con pandas; evita bucles fila a fila salvo necesidad.
- Documentacion: si cambia el flujo, archivos de entrada o estructura, actualizar README.md.
