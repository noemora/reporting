<!-- Instrucciones especificas para este workspace -->

- Proyecto: app de Streamlit para analisis de tickets y usabilidad (reporte comercial + logins).
- Arquitectura: app.py coordina el flujo -> data (carga/validacion/preproceso) -> dashboard (orquesta secciones) -> services/ui (tablas y graficos).
- Todo desarrollo debe regirse por principios SOLID.
- Mantener la separacion de responsabilidades: nada de logica pesada en app.py.
- Nuevas columnas o cambios de nombres: ajustar config/settings.py y, si aplica, data/validator.py.
- Nuevos KPIs o secciones: implementar en dashboard/orchestrator.py y usar helpers en services/ y ui/.
- UI en espanol, textos coherentes con el contexto del negocio.
- En Streamlit, cuando se creen elementos repetidos (especialmente en tabs, columnas o vistas paralelas), asignar key unicas y estables para evitar StreamlitDuplicateElementId.
- Prefiere operaciones vectorizadas con pandas; evita bucles fila a fila salvo necesidad.
- Documentacion: si cambia el flujo, archivos de entrada o estructura, actualizar README.md.
