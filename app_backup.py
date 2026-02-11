"""Streamlit app for ticket reporting and KPI analysis."""

# -----------------------------
# Imports
# -----------------------------
import io
import unicodedata
from typing import Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st


# -----------------------------
# Configuration / Constants
# -----------------------------
REQUIRED_COLUMNS: List[str] = [
    "ID del ticket",
    "Asunto",
    "Estado",
    "Prioridad",
    "Origen",
    "Tipo",
    "Agente",
    "Grupo",
    "Hora de creacion",
    "Tiempo de vencimiento",
    "Hora de resolucion",
    "Hora de cierre",
    "Hora de Ultima actualizacion",
    "Tiempo de respuesta inicial",
    "Tiempo transcurrido",
    "Tiempo de primera respuesta (en horas)",
    "Tiempo de resolucion (en horas)",
    "Interacciones del agente",
    "Interacciones del cliente",
    "Estado de resolucion",
    "Estado de primera respuesta",
    "Etiquetas",
    "Resultados de la encuesta",
    "Habilidad",
    "Tipo de asociacion",
    "El estado de cada respuesta",
    "Producto",
    "Ambiente",
    "Team Asignado",
    "Responsable Tk",
    "Url afectada",
    "Fecha Estimada",
    "Esfuerzo en Horas",
    "Modulo",
    "Nombre completo",
    "ID del contacto",
]

DATETIME_COLUMNS = [
    "Hora de creacion",
    "Tiempo de vencimiento",
    "Hora de resolucion",
    "Hora de cierre",
    "Hora de Ultima actualizacion",
    "Fecha Estimada",
]

NUMERIC_COLUMNS = [
    "Tiempo de primera respuesta (en horas)",
    "Tiempo de resolucion (en horas)",
    "Tiempo de respuesta inicial",
    "Tiempo transcurrido",
    "Interacciones del agente",
    "Interacciones del cliente",
    "Esfuerzo en Horas",
]

MONTH_NAMES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


# -----------------------------
# Utilities (text / column handling)
# -----------------------------
def normalize_col_name(value: str) -> str:
    """Normalize column names to make validation more tolerant."""
    value = fix_mojibake(value)
    value = value.strip().lower()
    value = unicodedata.normalize("NFKD", value)
    cleaned_chars = []
    for ch in value:
        if unicodedata.combining(ch):
            continue
        if ch.isalnum():
            cleaned_chars.append(ch)
        else:
            cleaned_chars.append(" ")
    value = "".join(cleaned_chars)
    value = " ".join(value.split())
    return value


def fix_mojibake(value: str) -> str:
    """Fix common mojibake sequences for Spanish accents."""
    replacements = {
        "Ã¡": "á",
        "Ã©": "é",
        "Ã­": "í",
        "Ã³": "ó",
        "Ãº": "ú",
        "Ã±": "ñ",
        "Ã“": "Ó",
        "Ãš": "Ú",
        "Ã": "Á",
        "Ã‰": "É",
        "Ã‘": "Ñ",
    }
    for bad, good in replacements.items():
        value = value.replace(bad, good)
    return value


def build_column_map(columns: List[str]) -> Dict[str, str]:
    """Map normalized names to actual column names found in the file."""
    normalized = {normalize_col_name(col): col for col in columns}
    return normalized


# -----------------------------
# Data loading / validation
# -----------------------------
@st.cache_data(show_spinner=False)
def load_excel(file_bytes: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")


def validate_and_standardize(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names and warn if core columns are missing."""
    df = df.copy()
    df = df.replace(r"^\s*$", pd.NA, regex=True)
    df = df.dropna(axis=1, how="all")

    normalized_map = build_column_map(df.columns.tolist())
    rename_map: Dict[str, str] = {}
    for required in REQUIRED_COLUMNS:
        key = normalize_col_name(required)
        actual = normalized_map.get(key)
        if actual is not None:
            rename_map[actual] = required

    df = df.rename(columns=rename_map)

    core_columns = [
        "ID del ticket",
        "Estado",
        "Hora de creacion",
        "Estado de resolucion",
        "Modulo",
        "Ambiente",
        "Grupo",
        "Tipo",
    ]
    missing_core = [col for col in core_columns if col not in df.columns]
    if missing_core:
        st.warning(
            "Faltan columnas clave para algunos cálculos: "
            + ", ".join(missing_core)
        )
        with st.expander("Ver columnas detectadas"):
            st.write(sorted(df.columns.tolist()))
    return df


# -----------------------------
# Data preparation
# -----------------------------
def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Parse dates, numeric fields, and create helper columns."""
    def clean_text_column(data: pd.Series) -> pd.Series:
        cleaned = data.astype(str).str.strip()
        cleaned = cleaned.replace("nan", pd.NA)
        return cleaned

    if "Modulo.1" in df.columns or "Modulo.2" in df.columns:
        df = df.drop(columns=[col for col in ["Modulo.1", "Modulo.2"] if col in df.columns])

    if "Producto" in df.columns and "Producto.1" in df.columns:
        producto_values = (
            df["Producto"]
            .astype(str)
            .str.strip()
            .str.lower()
            .replace("nan", "")
        )
        producto_is_placeholder = (
            producto_values.eq("") | producto_values.eq("no product")
        ).all()
        if producto_is_placeholder:
            df = df.drop(columns=["Producto"]).rename(columns={"Producto.1": "Producto"})

    for col in DATETIME_COLUMNS:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in [
        "Grupo",
        "Tipo",
        "Ambiente",
        "Estado",
        "Estado de resolucion",
        "Modulo",
    ]:
        if col in df.columns:
            df[col] = clean_text_column(df[col])

    df["Año"] = df["Hora de creacion"].dt.year
    df["Mes"] = df["Hora de creacion"].dt.month
    df["Mes Nombre"] = df["Mes"].map(MONTH_NAMES_ES)
    df["Mes Orden"] = df["Mes"]
    df["Periodo"] = df["Hora de creacion"].dt.to_period("M").dt.to_timestamp()

    df["Agente/Responsable"] = df["Responsable Tk"].where(
        df["Responsable Tk"].notna() & (df["Responsable Tk"].astype(str).str.strip() != ""),
        df["Agente"],
    )

    return df


# -----------------------------
# KPI calculations
# -----------------------------
def build_kpis(total_df: pd.DataFrame, resolved_df: pd.DataFrame | None = None) -> Dict[str, float]:
    """Compute main KPI metrics."""
    total = int(total_df["ID del ticket"].nunique())
    resolved_set = {"resuelto", "cerrado", "solucionado"}

    resolved_mask = (
        total_df["Estado de resolucion"].astype(str).str.lower().isin(resolved_set)
        | total_df["Estado"].astype(str).str.lower().isin(resolved_set)
    )
    source = resolved_df if resolved_df is not None else total_df
    if resolved_df is not None:
        resolved_mask = (
            resolved_df["Estado de resolucion"].astype(str).str.lower().isin(resolved_set)
            | resolved_df["Estado"].astype(str).str.lower().isin(resolved_set)
        )
    resolved = int(source.loc[resolved_mask, "ID del ticket"].nunique())

    resolution_rate = (resolved / total) if total else 0.0

    return {
        "total": total,
        "resolved": resolved,
        "resolution_rate": resolution_rate,
    }


# -----------------------------
# UI Components
# -----------------------------
def render_kpi_cards(kpis: Dict[str, float]) -> None:
    """Render KPI cards with a clean layout."""
    st.markdown(
        """
        <style>
        .kpi-card {
            background: #ffffff;
            padding: 16px;
            border-radius: 12px;
            border: 1px solid #e6e6e6;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }
        .kpi-title { font-size: 14px; color: #6b6b6b; margin-bottom: 6px; }
        .kpi-value { font-size: 24px; font-weight: 700; color: #111827; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    col1.markdown(
        f"<div class='kpi-card'><div class='kpi-title'>Total tickets</div><div class='kpi-value'>{kpis['total']}</div></div>",
        unsafe_allow_html=True,
    )
    col2.markdown(
        f"<div class='kpi-card'><div class='kpi-title'>Tickets resueltos</div><div class='kpi-value'>{kpis['resolved']}</div></div>",
        unsafe_allow_html=True,
    )
    col3.markdown(
        f"<div class='kpi-card'><div class='kpi-title'>Tasa de resolución</div><div class='kpi-value'>{kpis['resolution_rate']:.1%}</div></div>",
        unsafe_allow_html=True,
    )


def render_hybrid_dashboard(df: pd.DataFrame) -> None:
    """Render hybrid dashboard with KPI cards + calculos-style table."""
    card_placeholder = st.container()

    st.subheader("Filtros")

    col1, col2, col3 = st.columns(3)
    with col1:
        year_options = sorted(df["Año"].dropna().unique())
        current_year = pd.Timestamp.today().year
        year_index = 0
        if year_options:
            year_index = min(
                range(len(year_options)),
                key=lambda idx: abs(year_options[idx] - current_year),
            )
        selected_year = (
            st.selectbox("Año", year_options, index=year_index, key="hybrid_year")
            if year_options
            else None
        )
    with col2:
        client_options = sorted(df["Grupo"].dropna().unique())
        selected_client = (
            st.selectbox("Cliente (Grupo)", ["Todos"] + client_options, key="hybrid_cliente")
            if client_options
            else "Todos"
        )
    with col3:
        tipos = st.multiselect(
            "Tipo",
            sorted(df["Tipo"].dropna().unique()),
            key="hybrid_tipo",
        )

    base_filtered = df.copy()
    if selected_client and selected_client != "Todos":
        base_filtered = base_filtered[base_filtered["Grupo"] == selected_client]
    if tipos:
        base_filtered = base_filtered[base_filtered["Tipo"].isin(tipos)]

    filtered = base_filtered.copy()
    if selected_year is not None:
        filtered = filtered[filtered["Año"] == selected_year]

    if filtered.empty:
        st.warning("No hay datos para los filtros seleccionados.")
        return

    with card_placeholder:
        resolved_df = base_filtered.copy()
        if selected_year is not None and "Hora de resolucion" in resolved_df.columns:
            resolved_df = resolved_df[
                pd.to_datetime(resolved_df["Hora de resolucion"], errors="coerce").dt.year
                == selected_year
            ]
        kpis = build_kpis(filtered, resolved_df)
        render_kpi_cards(kpis)

    filtered = filtered.dropna(subset=["Hora de creacion"])
    filtered["Mes"] = filtered["Hora de creacion"].dt.month

    ambiente_norm = (
        filtered["Ambiente"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace("ó", "o")
    )
    prod_envs = {"prod (cliente)", "produccion", "produccion ", "prod"}
    filtered_prod = filtered[ambiente_norm.isin(prod_envs)].copy()

    st.subheader("Incidentes y consulta de informacion")
    month_order = list(range(1, 13))

    created_counts = (
        filtered_prod.groupby(filtered_prod["Hora de creacion"].dt.month)[
            "ID del ticket"
        ]
        .nunique()
        .reindex(month_order, fill_value=0)
    )

    resolved_set = {"resuelto", "cerrado", "solucionado", "resueltos"}
    resolved_base = base_filtered.copy()
    if selected_year is not None and "Hora de resolucion" in resolved_base.columns:
        resolved_base = resolved_base[
            pd.to_datetime(resolved_base["Hora de resolucion"], errors="coerce").dt.year
            == selected_year
        ]
    ambiente_norm_res = (
        resolved_base["Ambiente"]
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace("ó", "o")
    )
    resolved_prod = resolved_base[ambiente_norm_res.isin(prod_envs)].copy()
    resolved_mask = (
        resolved_prod["Estado de resolucion"].astype(str).str.lower().isin(resolved_set)
        | resolved_prod["Estado"].astype(str).str.lower().isin(resolved_set)
    )
    resolved_counts = (
        resolved_prod[resolved_mask]
        .groupby(pd.to_datetime(resolved_prod["Hora de resolucion"], errors="coerce").dt.month)[
            "ID del ticket"
        ]
        .nunique()
        .reindex(month_order, fill_value=0)
    )

    incidents_table = pd.DataFrame(
        {
            MONTH_NAMES_ES[m]: [created_counts[m], resolved_counts[m]]
            for m in month_order
        },
        index=["Tickets enviados por cliente", "Tickets atendidos por N5"],
    )
    incidents_table.index.name = "Recepcion/atencion de tickets"
    incidents_table = incidents_table.fillna(0)
    incidents_table["Total"] = incidents_table.sum(axis=1)
    # incidents_table.loc["Total"] = incidents_table.sum(axis=0)
    st.dataframe(incidents_table, use_container_width=True)

    def missing_ids(df_source: pd.DataFrame, column: str) -> list:
        values = df_source[column].astype(str).str.strip()
        mask = df_source[column].isna() | values.eq("")
        return df_source.loc[mask, "ID del ticket"].dropna().unique().tolist()

    missing_modulo_ids = missing_ids(filtered_prod, "Modulo")
    missing_resolucion_ids = missing_ids(filtered_prod, "Estado de resolucion")
    missing_ambiente_ids = missing_ids(filtered, "Ambiente")
    missing_estado_ids = missing_ids(filtered_prod, "Estado")

    with st.expander("Detalle de tickets con campos vacíos"):
        if missing_estado_ids:
            st.write("Estado (productivo):", missing_estado_ids)
        if missing_modulo_ids:
            st.write("Módulo (productivo):", missing_modulo_ids)
        if missing_resolucion_ids:
            st.write("Estado de resolución (productivo):", missing_resolucion_ids)
        if missing_ambiente_ids:
            st.write("Ambiente:", missing_ambiente_ids)

    st.subheader("Conteo por estado")
    # estado_options = sorted(filtered_prod["Estado"].dropna().unique())
    # estados_seleccionados = st.multiselect(
    #     "Filtrar estados",
    #     estado_options,
    #     key="filter_estado_table",
    # )
    estados_seleccionados = []
    estado_df = (
        filtered_prod[filtered_prod["Estado"].isin(estados_seleccionados)]
        if estados_seleccionados
        else filtered_prod
    )
    estado_df = estado_df.copy()
    estado_df["Estado"] = estado_df["Estado"].fillna("Sin estado")
    pivot = (
        estado_df.pivot_table(
            index="Estado",
            columns="Mes",
            values="ID del ticket",
            aggfunc="nunique",
            fill_value=0,
        )
        .sort_index()
    )

    month_order = list(range(1, 13))
    pivot = pivot.reindex(columns=month_order)
    pivot = pivot.fillna(0)
    pivot.columns = [MONTH_NAMES_ES.get(m, str(m)) for m in pivot.columns]
    pivot["Total"] = pivot.sum(axis=1)
    pivot.loc["Total"] = pivot.sum(axis=0)
    st.dataframe(pivot, use_container_width=True)

    render_trend_chart(
        estado_df,
        category_col="Estado",
        selected_year=selected_year,
        title="Tendencia de estado por mes",
    )

    st.subheader("Conteo por módulo")
    # modulo_options = sorted(filtered_prod["Modulo"].dropna().unique())
    # modulos_seleccionados = st.multiselect(
    #     "Filtrar módulos",
    #     modulo_options,
    #     key="filter_modulo_table",
    # )
    modulos_seleccionados = []
    modulo_df = (
        filtered_prod[filtered_prod["Modulo"].isin(modulos_seleccionados)]
        if modulos_seleccionados
        else filtered_prod
    )
    modulo_df = modulo_df.copy()
    modulo_df["Modulo"] = modulo_df["Modulo"].fillna("Sin módulo")
    module_pivot = (
        modulo_df.pivot_table(
            index="Modulo",
            columns="Mes",
            values="ID del ticket",
            aggfunc="nunique",
            fill_value=0,
        )
        .sort_index()
    )
    module_pivot = module_pivot.reindex(columns=month_order)
    module_pivot = module_pivot.fillna(0)
    module_pivot.columns = [MONTH_NAMES_ES.get(m, str(m)) for m in module_pivot.columns]
    module_pivot["Total"] = module_pivot.sum(axis=1)
    module_pivot.loc["Total"] = module_pivot.sum(axis=0)
    st.dataframe(module_pivot, use_container_width=True)

    render_trend_chart(
        modulo_df,
        category_col="Modulo",
        selected_year=selected_year,
        title="Tendencia de módulo por mes",
    )

    st.subheader("Conteo por ambiente")
    # ambiente_options = sorted(filtered["Ambiente"].dropna().unique())
    # ambientes_seleccionados = st.multiselect(
    #     "Filtrar ambientes",
    #     ambiente_options,
    #     key="filter_ambiente_table",
    # )
    ambientes_seleccionados = []
    ambiente_df = (
        filtered[filtered["Ambiente"].isin(ambientes_seleccionados)]
        if ambientes_seleccionados
        else filtered
    )
    ambiente_df = ambiente_df.copy()
    ambiente_df["Ambiente"] = ambiente_df["Ambiente"].fillna("Sin ambiente")

    # with st.expander("Diagnóstico QA Abril 2025"):
    #     qa_mask = ambiente_df["Ambiente"].astype(str).str.strip().str.lower().eq("qa")
    #     april_mask = ambiente_df["Mes"] == 4
    #     qa_april = ambiente_df[qa_mask & april_mask]
    #     st.write("Registros QA Abril 2025:", qa_april["ID del ticket"].nunique())
    #     if not qa_april.empty:
    #         st.dataframe(
    #             qa_april[["ID del ticket", "Hora de creacion", "Ambiente", "Grupo", "Tipo"]],
    #             use_container_width=True,
    #         )
    ambiente_pivot = (
        ambiente_df.pivot_table(
            index="Ambiente",
            columns="Mes",
            values="ID del ticket",
            aggfunc="nunique",
            fill_value=0,
        )
        .sort_index()
    )
    ambiente_pivot = ambiente_pivot.reindex(columns=month_order)
    ambiente_pivot.columns = [MONTH_NAMES_ES.get(m, str(m)) for m in ambiente_pivot.columns]
    ambiente_pivot["Total"] = ambiente_pivot.sum(axis=1)
    ambiente_pivot.loc["Total"] = ambiente_pivot.sum(axis=0)
    st.dataframe(ambiente_pivot, use_container_width=True)

    render_trend_chart(
        ambiente_df,
        category_col="Ambiente",
        selected_year=selected_year,
        title="Tendencia de ambiente por mes",
    )

    st.subheader("Conteo por estado de resolución")
    # resolucion_options = sorted(filtered_prod["Estado de resolucion"].dropna().unique())
    # resoluciones_seleccionadas = st.multiselect(
    #     "Filtrar estado de resolución",
    #     resolucion_options,
    #     key="filter_resolucion_table",
    # )
    resoluciones_seleccionadas = []
    resolucion_df = (
        filtered_prod[filtered_prod["Estado de resolucion"].isin(resoluciones_seleccionadas)]
        if resoluciones_seleccionadas
        else filtered_prod
    )
    resolucion_df = resolucion_df.copy()
    resolucion_df["Estado de resolucion"] = resolucion_df["Estado de resolucion"].fillna(
        "Sin estado de resolución"
    )
    resolucion_pivot = (
        resolucion_df.pivot_table(
            index="Estado de resolucion",
            columns="Mes",
            values="ID del ticket",
            aggfunc="nunique",
            fill_value=0,
        )
        .sort_index()
    )
    resolucion_pivot = resolucion_pivot.reindex(columns=month_order)
    resolucion_pivot = resolucion_pivot.fillna(0)
    resolucion_pivot.columns = [MONTH_NAMES_ES.get(m, str(m)) for m in resolucion_pivot.columns]
    resolucion_pivot["Total"] = resolucion_pivot.sum(axis=1)
    resolucion_index = resolucion_pivot.index.astype(str).str.lower()
    violated_mask = resolucion_index.str.contains("sla") & resolucion_index.str.contains("violat")
    if violated_mask.any():
        violated_row = resolucion_pivot.loc[violated_mask].iloc[0]
        month_cols = [col for col in resolucion_pivot.columns if col != "Total"]
        totals_by_col = resolucion_pivot[month_cols].sum(axis=0)
        totals_all = totals_by_col.sum()
        percent_row = (violated_row[month_cols] / totals_by_col.replace(0, pd.NA))
        percent_total = (
            violated_row[month_cols].sum() / totals_all if totals_all else 0
        )
        percent_values = [
            f"{value * 100:.1f}%" if pd.notna(value) else "0.0%"
            for value in percent_row.values
        ]
        percent_values.append(f"{percent_total * 100:.1f}%")
        resolucion_pivot.loc["SLA violated %"] = percent_values
    st.dataframe(resolucion_pivot, use_container_width=True)

    render_trend_chart(
        resolucion_df,
        category_col="Estado de resolucion",
        selected_year=selected_year,
        title="Tendencia de estado de resolución por mes",
    )


def render_trend_chart(
    df: pd.DataFrame,
    category_col: str,
    selected_year: int | None,
    title: str,
) -> None:
    """Render a monthly trend chart with labels for all points."""
    trend = (
        df.groupby(["Periodo", category_col])["ID del ticket"]
        .nunique()
        .reset_index()
    )

    if selected_year is not None:
        all_months = pd.date_range(
            start=f"{int(selected_year)}-01-01",
            end=f"{int(selected_year)}-12-01",
            freq="MS",
        )
    else:
        all_months = pd.to_datetime(sorted(df["Periodo"].dropna().unique()))

    all_categories = sorted(df[category_col].dropna().unique())
    full_index = pd.MultiIndex.from_product(
        [all_months, all_categories],
        names=["Periodo", category_col],
    )
    trend = (
        trend.set_index(["Periodo", category_col])
        .reindex(full_index, fill_value=0)
        .reset_index()
    )

    fig = px.line(
        trend,
        x="Periodo",
        y="ID del ticket",
        color=category_col,
        markers=True,
        text="ID del ticket",
        labels={
            "Periodo": "Mes",
            "ID del ticket": "Tickets",
            category_col: title.replace("Tendencia de ", "").replace(" por mes", ""),
        },
    )
    fig.update_traces(textposition="top center", texttemplate="%{y}")
    tick_vals = sorted(trend["Periodo"].unique())
    tick_text = [MONTH_NAMES_ES.get(pd.Timestamp(val).month, "") for val in tick_vals]
    fig.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(tickmode="array", tickvals=tick_vals, ticktext=tick_text),
    )
    st.subheader(title)
    st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# App entry point
# -----------------------------
def main() -> None:
    st.set_page_config(page_title="Informes Gerenciales de Tickets", layout="wide")
    st.title("Informes Gerenciales de Tickets")
    st.caption("Carga un Excel, filtra y analiza KPIs de tickets.")

    uploaded_file = st.file_uploader(
        "Carga el archivo Excel", type=["xlsx"], accept_multiple_files=False
    )

    if not uploaded_file:
        st.info("Carga un archivo Excel para iniciar el análisis.")
        return

    df = load_excel(uploaded_file.getvalue())
    df = validate_and_standardize(df)
    df = preprocess(df)

    render_hybrid_dashboard(df)


if __name__ == "__main__":
    main()
