import os
import numpy as np
import pandas as pd
import streamlit as st
import altair as alt

# ---------------------------
# Configuración general
# ---------------------------
st.set_page_config(page_title="Ranking PPR 0101 – Visualizador 2021", layout="wide")

# Hotfix: asegurar motor de Excel (evita ImportError en despliegues)
try:
    import openpyxl  # noqa: F401
    EXCEL_ENGINE = "openpyxl"
except ImportError:
    st.error("Falta la librería **openpyxl** para leer archivos .xlsx. "
             "Agrega `openpyxl==3.1.2` a `requirements.txt` y vuelve a desplegar.")
    st.stop()

# ---------------------------
# Utilidades
# ---------------------------
DEFAULT_PATHS = [
    "data/PPR 0101-2021.xlsx",  # recomendado
    "PPR 0101-2021.xlsx",       # por si lo ponen en la raíz
]

def to_title(txt):
    if txt is None:
        return None
    return str(txt).replace("_", " ").title()

def find_col(df, candidates):
    # Devuelve el primer encabezado que matchee por igualdad o contiene (case-insensitive)
    cols = {str(c).strip(): c for c in df.columns}
    low = {k.lower(): v for k, v in cols.items()}
    for pat in candidates:
        p = str(pat).lower()
        # exacto
        if p in low:
            return low[p]
        # contiene
        for k, orig in low.items():
            if p in k:
                return orig
    return None

def debug_listing():
    # Muestra contenido de carpetas para diagnóstico en Streamlit Cloud
    from pathlib import Path
    roots = [".", "data"]
    out = []
    for r in roots:
        p = Path(r)
        if p.exists():
            out.append(f"📁 {p.resolve()}")
            for child in sorted(p.iterdir()):
                out.append(" ├─ " + child.name)
        else:
            out.append(f"(pasta inexistente) {r}")
    return "```\n" + "\n".join(out) + "\n```"

@st.cache_data(show_spinner=True)
def try_read_excel(paths):
    last_err = None
    for p in paths:
        if os.path.exists(p):
            try:
                df = pd.read_excel(p, engine=EXCEL_ENGINE)
                df.columns = [str(c).strip() for c in df.columns]
                return df, p
            except Exception as e:
                last_err = e
        else:
            last_err = FileNotFoundError(f"No existe: {p}")
    raise last_err if last_err else FileNotFoundError("Archivo no encontrado.")

# ---------------------------
# Carga de datos (con fallback a uploader)
# ---------------------------
st.title("🏅 Ranking PPR 0101 – 2021")
st.caption("Visualizador llamativo, didáctico e interactivo.")

df, data_source = None, None
try:
    df, data_source = try_read_excel(DEFAULT_PATHS)
except Exception:
    st.warning("⚠️ No pude abrir el Excel en los caminos estándar. "
               "Verifica la ruta o **sube el archivo** abajo.")
    st.markdown("**Contenido de carpetas (diagnóstico):**")
    st.markdown(debug_listing())
    up = st.file_uploader("Sube el Excel (.xlsx)", type=["xlsx"])
    if up is not None:
        try:
            df = pd.read_excel(up, engine=EXCEL_ENGINE)
            df.columns = [str(c).strip() for c in df.columns]
            data_source = f"upload: {up.name}"
        except Exception as e2:
            st.error(f"Error al leer el upload: {e2}")

if df is None:
    st.stop()

st.caption(f"✅ Datos cargados de: **{data_source}**")

# ---------------------------
# Detección de columnas (robusta a variaciones)
# ---------------------------
col_entidad   = find_col(df, ["gobierno", "entidad", "municipalidad", "gobierno local", "nombre", "region", "unidad"])
col_tipo      = find_col(df, ["tipo", "nivel de gobierno", "tipo gobierno", "gobierno regional", "gobierno local"])
col_pia       = find_col(df, ["pia", "presupuesto inicial de apertura"])
col_pim       = find_col(df, ["pim", "presupuesto institucional modificado"])
col_avance    = find_col(df, ["avance %", "avance%", "avance", "ejecución", "ejecucion"])
col_poblacion = find_col(df, ["población", "poblacion", "hab", "habitantes"])
col_punt_pim  = find_col(df, ["puntaje pim", "punt pim", "score pim"])
col_punt_av   = find_col(df, ["puntaje avance", "punt avance", "score avance"])
col_punt_pop  = find_col(df, ["puntaje población", "punt poblacion", "score poblacion"])
col_total     = find_col(df, ["total", "puntaje total", "score total", "orden presupuestal total"])
col_orden     = find_col(df, ["orden presupuestal", "ranking", "posicion", "posición"])

# Copia de trabajo + métricas derivadas
df_work = df.copy()

if col_pia and col_pim:
    df_work["Crec_PIM_vs_PIA_%"] = np.where(
        (pd.to_numeric(df_work[col_pia], errors="coerce") > 0) & pd.to_numeric(df_work[col_pim], errors="coerce").notna(),
        (pd.to_numeric(df_work[col_pim], errors="coerce") / pd.to_numeric(df_work[col_pia], errors="coerce") - 1) * 100,
        np.nan
    )
else:
    df_work["Crec_PIM_vs_PIA_%"] = np.nan

if col_pim and col_poblacion:
    pop = pd.to_numeric(df_work[col_poblacion], errors="coerce")
    pim = pd.to_numeric(df_work[col_pim], errors="coerce")
    df_work["PIM_per_cápita"] = np.where((pop > 0) & pim.notna(), pim / pop, np.nan)
else:
    df_work["PIM_per_cápita"] = np.nan

# Normalizar Avance % si viene entre 0-1
if col_avance and df_work[col_avance].notna().mean() > 0:
    s = pd.to_numeric(df_work[col_avance], errors="coerce").dropna().head(30)
    if not s.empty and (s.between(0, 1).mean() > 0.7):
        df_work[col_avance] = pd.to_numeric(df_work[col_avance], errors="coerce") * 100

# ---------------------------
# Sidebar: filtros y descarga
# ---------------------------
with st.sidebar:
    st.header("Filtros")
    if col_tipo:
        tipos = ["(Todos)"] + sorted([t for t in df_work[col_tipo].dropna().astype(str).unique()])
        sel_tipo = st.selectbox("Tipo de gobierno", tipos, index=0)
    else:
        sel_tipo = "(Todos)"
    top_n = st.slider("Top N (por Puntaje Total o Avance % si no hay total)", 5, 50, 15, 1)
    st.markdown("---")
    st.subheader("Descarga datos filtrados")
    if st.button("Generar CSV"):
        tmp = df_work.copy()
        if col_tipo and sel_tipo != "(Todos)":
            tmp = tmp[tmp[col_tipo].astype(str) == sel_tipo]
        csv = tmp.to_csv(index=False).encode("utf-8")
        st.download_button("Descargar CSV", data=csv, file_name="ppr0101_filtrado.csv", mime="text/csv")

# Aplicar filtro principal
if col_tipo and sel_tipo != "(Todos)":
    data = df_work[df_work[col_tipo].astype(str) == sel_tipo].copy()
else:
    data = df_work.copy()

# ---------------------------
# Texto explicativo (tu contenido)
# ---------------------------
st.markdown("""
**Propósito principal:** Reporte estadístico anual que evalúa la programación y el cumplimiento del presupuesto (PPR 0101) asignado y ejecutado por gobiernos locales y regionales del Perú. Finalidad específica 2021: **“INCREMENTO DE LA PRÁCTICA DE ACTIVIDADES FÍSICAS, DEPORTIVAS Y RECREATIVAS EN LA POBLACIÓN PERUANA”.**  
**Entidades evaluadas:** Gobiernos locales (municipalidades provinciales y distritales) y gobiernos regionales.  
**Fuente de datos:** DNCTD (base); Portal de Transparencia Económica – *Consulta Amigable* (PIA, PIM, Avance %, puntajes); INEI (población 2019).  
**PIA:** Presupuesto Inicial de Apertura (aprobado inicialmente). **PIM:** Presupuesto Institucional Modificado (actualizado durante el año fiscal).  
**Puntaje Total:** Suma de puntajes por **PIM**, **Avance %** y **Población** según rangos/leyendas definidas.  
**Avance %:** Ejecución de ingresos (Recaudado) y gastos (Compromiso, Devengado, Girado).  
**Población:** Contextualiza el tamaño de beneficiarios e incide en el puntaje por rango.  
**Orden presupuestal:** Posición en el ranking según desempeño en ejecución y cumplimiento.
""")

# ---------------------------
# Pestañas: no repetir contenidos entre gráficos/tabla
# ---------------------------
tabs = st.tabs(["📊 Ranking & Resumen", "📈 PIA vs PIM (comparaciones)", "🟢 Avance % vs PIM (eficiencia/tamaño)", "📋 Tabla exploratoria"])

# ----- TAB 1: Ranking -----
with tabs[0]:
    st.subheader("Top por desempeño (sin duplicar vistas de otras pestañas)")
    # Métrica de ranking
    rank_metric = col_total if col_total else (col_avance if col_avance else col_pim)
    rank_label = to_title(rank_metric) if rank_metric else "Métrica"
    st.write(f"Ordenado por **{rank_label}**.")
    tmp = data.copy()
    if rank_metric:
        tmp = tmp.sort_values(rank_metric, ascending=False).head(top_n)
    else:
        tmp = tmp.head(top_n)
    ent_name = col_entidad if col_entidad else (col_orden if col_orden else tmp.columns[0])
    chart = alt.Chart(tmp).mark_bar().encode(
        x=alt.X(f"{rank_metric}:Q", title=rank_label) if rank_metric else alt.X(tmp.columns[1]),
        y=alt.Y(f"{ent_name}:N", sort="-x", title=to_title(ent_name)),
        tooltip=[ent_name] + [c for c in [col_pia, col_pim, col_avance, col_poblacion, col_total, col_orden] if c]
    ).properties(height=520)
    st.altair_chart(chart, use_container_width=True)
    st.markdown("""
**Cómo leer:** Esta vista muestra el **desempeño agregado** (Puntaje Total).  
Si no hay Puntaje Total en tu base, usa **Avance %** como proxy.  
A mayor **PIM** no siempre mayor ranking: la **eficiencia de ejecución (Avance %)** pesa.
""")

# ----- TAB 2: PIA vs PIM -----
with tabs[1]:
    st.subheader("Variaciones presupuestales (comparaciones por entidad)")
    if col_pia and col_pim:
        sample_list = data[ent_name].dropna().astype(str).unique().tolist()
        pick = st.multiselect("Seleccione hasta 15 entidades para comparar PIA vs PIM", sample_list, max_selections=15)
        df_cmp = data.copy()
        if pick:
            df_cmp = df_cmp[df_cmp[ent_name].astype(str).isin(pick)]
        dfm = df_cmp[[ent_name, col_pia, col_pim]].melt(id_vars=[ent_name], var_name="Tipo", value_name="Monto")
        chart2 = alt.Chart(dfm).mark_bar().encode(
            x=alt.X("Tipo:N", title="PIA vs PIM"),
            y=alt.Y("Monto:Q", title="Soles"),
            column=alt.Column(f"{ent_name}:N", title=None),
            tooltip=[ent_name, "Tipo", alt.Tooltip("Monto:Q", format=",.0f")]
        ).resolve_scale(y='independent')
        st.altair_chart(chart2, use_container_width=True)

        st.markdown("""
**Qué mirar:** Cambios de **PIA → PIM** reflejan modificaciones presupuestarias.  
Use **Crec_PIM_vs_PIA_%** para detectar aumentos/disminuciones relativos.
""")
        show_cols = [c for c in [ent_name, col_pia, col_pim, "Crec_PIM_vs_PIA_%", "PIM_per_cápita"] if c in data.columns]
        if show_cols:
            st.dataframe(data[show_cols].head(1000))
    else:
        st.info("No se detectaron columnas identificables como PIA y PIM. Revisa los encabezados del archivo.")

# ----- TAB 3: Avance % vs PIM -----
with tabs[2]:
    st.subheader("Eficiencia (Avance %) vs Tamaño (PIM)")
    if col_avance and col_pim:
        base = data.dropna(subset=[col_avance, col_pim]).copy()
        if col_poblacion:
            size_enc = alt.Size(f"{col_poblacion}:Q", title="Población", scale=alt.Scale(range=[30, 400]))
            tooltip = [ent_name,
                       alt.Tooltip(f"{col_avance}:Q", title="Avance %", format=".1f"),
                       alt.Tooltip(f"{col_pim}:Q", title="PIM", format=",.0f"),
                       alt.Tooltip(f"{col_poblacion}:Q", title="Población", format=",.0f")]
        else:
            size_enc = alt.value(80)
            tooltip = [ent_name,
                       alt.Tooltip(f"{col_avance}:Q", title="Avance %", format=".1f"),
                       alt.Tooltip(f"{col_pim}:Q", title="PIM", format=",.0f")]
        color_enc = alt.Color(f"{col_tipo}:N", title=to_title(col_tipo)) if col_tipo else alt.value("#1f77b4")
        scatter = alt.Chart(base).mark_circle(opacity=0.72).encode(
            x=alt.X(f"{col_pim}:Q", title="PIM (Soles)", scale=alt.Scale(zero=False)),
            y=alt.Y(f"{col_avance}:Q", title="Avance %", scale=alt.Scale(domain=[0, 110])),
            color=color_enc,
            size=size_enc,
            tooltip=tooltip
        ).properties(height=520)
        st.altair_chart(scatter, use_container_width=True)
        st.markdown("""
**Cómo leer:** Cada punto es una entidad.  
Eje **X** = **PIM** (tamaño del presupuesto), Eje **Y** = **Avance %** (eficiencia).  
El **tamaño** del punto (si está disponible) representa **Población**.  
Busque **outliers**: grande con bajo avance, o pequeño con alto avance.
""")
    else:
        st.info("Faltan columnas para construir la comparación (Avance % y/o PIM).")

# ----- TAB 4: Tabla (sin repetir los gráficos) -----
with tabs[3]:
    st.subheader("Tabla exploratoria (sin duplicar vistas anteriores)")
    cols_table = []
    base_candidates = [ent_name, col_orden, col_total, col_poblacion, "PIM_per_cápita", "Crec_PIM_vs_PIA_%"]
    for c in base_candidates:
        if c and c in data.columns and c not in cols_table:
            cols_table.append(c)
    if not cols_table:
        cols_table = data.columns.tolist()[:8]
    try:
        sort_col = col_orden if col_orden in cols_table else cols_table[0]
        st.dataframe(data[cols_table].sort_values(sort_col).head(1000))
    except Exception:
        st.dataframe(data[cols_table].head(1000))

st.markdown("---")
with st.expander("ℹ️ Glosario PPR 0101 (2021)"):
    st.markdown("""
- **Propósito principal:** Evaluar programación y cumplimiento del presupuesto PPR 0101 (2021) para incrementar la práctica de actividades físicas, deportivas y recreativas.  
- **Entidades evaluadas:** Gobiernos locales (municipalidades) y gobiernos regionales.  
- **Fuentes:** DNCTD (base); Transparencia Económica - *Consulta Amigable* (PIA, PIM, Avance % y puntajes); INEI (población 2019).  
- **PIA:** Presupuesto Inicial de Apertura aprovado por el Titular.  
- **PIM:** Presupuesto Institucional Modificado tras incorporaciones y modificaciones.  
- **Total (puntaje):** Suma de puntajes por PIM, Avance % y Población.  
- **Avance %:** Ejecución de ingresos (Recaudado) y gastos (Compromiso/Devengado/Girado).  
- **Población:** Variable para ponderar/contextualizar el impacto.  
- **Orden presupuestal:** Ranking según desempeño en ejecución y cumplimiento.
""")

st.success("✅ Listo. Explora con los filtros (Tipo de gobierno, Top N) y descarga el CSV filtrado desde la barra lateral.")
