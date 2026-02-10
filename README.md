# Sistema de Informes Gerenciales de Tickets

Aplicación en Streamlit para cargar archivos Excel de tickets, aplicar filtros interactivos y visualizar KPIs y gráficos gerenciales.

## Requisitos
- Python 3.9+

## Instalación
1. Crear y activar un entorno virtual.
2. Instalar dependencias:
   - `pip install -r requirements.txt`

## Ejecución
- `streamlit run app.py`

## Estructura de carpetas
- data/ : Archivos de datos (opcional).
- src/ : Módulos auxiliares (opcional).
- assets/ : Recursos estáticos (logos, imágenes).
- app.py : Aplicación principal.
- requirements.txt : Dependencias.

## Ejemplos de uso
1. Ejecuta la app.
2. Carga un archivo Excel con las columnas requeridas.
3. Ajusta los filtros del panel izquierdo.
4. Revisa KPIs, gráficos y tabla resumen.
5. Descarga los datos filtrados desde la opción de exportación.

## Columnas requeridas
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
- Esfuerzo en Horas, Modulo, Nombre completo
- ID del contacto, Nombre de la compañía
