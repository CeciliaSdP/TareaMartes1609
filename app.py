
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from io import BytesIO

st.set_page_config(page_title="Ranking PPR 0101 – Visualizador 2021", layout="wide")

def find_col(df, candidates):
    cols = {str(c).lower(): c for c in df.columns}
    for pat in candidates:
        for k, orig in cols.items():
            if k == pat.lower() or pat.lower() in k:
                return orig
    return None

@st.cache_data
def load_data(path):
    df = pd.read_excel(path)
    df.columns = [str(c).strip() for c in df.columns]
    return df

def to_title(txt):
    if txt is None:
        return None
    return str(txt).replace("_", " ").title()

DATA_PATH = "data/PPR 0101-2021.xlsx"
df = load_data(DATA_PATH)

col_entidad = find_col(df, ["gobierno", "entidad", "municipalidad", "gobierno local", "nombre", "region", "unidad"])
col_tipo = find_col(df, ["tipo", "nivel de gobierno", "tipo gobierno", "gobierno regional", "gobierno local"])
col_pia = find_col(df, ["pia", "presupuesto inicial de apertura"])
col_pim = find_col(df, ["pim", "presupuesto institucional modificado"])
col_avance = find_col(df, ["avance %", "avance%", "avance", "ejecución", "ejecucion"])
col_poblacion = find_col(df, ["población", "poblacion", "hab", "habitantes"])
col_punt_pim = find_col(df, ["puntaje pim", "punt pim", "score pim"])
col_punt_av = find_col(df, ["puntaje avance", "punt avance", "score avance"])
col_punt_pop = find_col(df, ["puntaje población", "punt poblacion", "score poblacion"])
col_total = find_col(df, ["total", "puntaje total", "score total", "orden presupuestal total"])
col_orden = find_col(df, ["orden presupuestal", "ranking", "posicion", "posición"])

df_work = df.copy()

if col_pia and col_pim:
    df_work["Crec_PIM_vs_PIA_%"] = np.where((df_work[col_pia] > 0) & df_work[col_pim].notna(),
                                            (df_work[col_pim] / df_work[col_pia] - 1) * 100, np.nan)
else:
    df_work["Crec_PIM_vs_PIA_%"] = np.nan

if col_pim and col_poblacion:
    df_work["PIM_per_cápita"] = np.where((df_work[col_poblacion] > 0) & df_work[col_pim].notna(),
                                        df_work[col_pim] / df_work[col_poblacion], np.nan)
else:
    df_work["PIM_per_cápita"] = np.nan

if col_avance and df_work[col_avance].notna().mean() > 0:
    sample = df_work[col_avance].dropna().head(20)
    if not sample.empty and sample.between(0,1).mean() > 0.7:
        df_work[col_avance] = df_work[col_avance] * 100

with st.sidebar:
    st.header("Filtros")
    if col_tipo:
        tipos = ["(Todos)"] + sorted([t for t in df_work[col_tipo].dropna().astype(str).unique()])
        sel_tipo = st.selectbox("Tipo de gobierno", tipos, index=0)
    else:
        sel_tipo = "(Todos)"
    top_n = st.slider("Top N (por puntaje total o por Avance % si no hay total)", min_value=5, max_value=50, value=15, step=1)
    st.markdown("---")
    st.subheader("Descarga")
    if st.button("Descargar datos filtrados (CSV)"):
        tmp = df_work.copy()
        if col_tipo and sel_tipo != "(Todos)":
            tmp = tmp[tmp[col_tipo].astype(str) == sel_tipo]
        csv = tmp.to_csv(index=False).encode("utf-8")
        st.download_button("Bajar CSV", data=csv, file_name="ppr0101_filtrado.csv", mime="text/csv")

if col_tipo and sel_tipo != "(Todos)":
    data = df_work[df_work[col_tipo].astype(str) == sel_tipo].copy()
else:
    data = df_work.copy()

st.title("🏅 Ranking PPR 0101 – 2021")
st.caption("Propósito: Reporte estadístico anual que evalúa programación y cumplimiento del presupuesto asignado y ejecutado por gobiernos locales y regionales del Perú. Finalidad: Incremento de la práctica de actividades físicas, deportivas y recreativas en 2021.")
st.markdown('''
**Ámbito evaluado:** Gobiernos locales (municipalidades de provincias y distritos) y gobiernos regionales.  
**Fuente:** DNCTD; variables presupuestales del Portal de Transparencia Económica (Consulta Amigable); población del INEI (Censo 2019).  
**PIA:** Presupuesto Inicial aprobado para el año fiscal. **PIM:** Presupuesto actualizado durante el año tras modificaciones.  
**Puntaje Total:** Suma de puntajes por PIM, Avance % y Población según rangos definidos.  
**Avance %:** Ejecución de ingresos (Recaudado) y gastos (Compromiso/Devengado/Girado).  
**Población:** Variable para ponderar y contextualizar el impacto.  
**Orden presupuestal:** Ranking según desempeño en ejecución y cumplimiento.
''')

tabs = st.tabs(["📊 Ranking & Resumen", "📈 Comparaciones PIA vs PIM", "🟢 Eficiencia (Avance %) vs Tamaño (PIM)", "📋 Tabla exploratoria"])

with tabs[0]:
    st.subheader("Top por desempeño")
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
    ).properties(height=500)
    st.altair_chart(chart, use_container_width=True)
    st.markdown('''
**Lectura sugerida:** Esta vista prioriza el desempeño agregado (Puntaje Total). Si no existiese la columna de puntaje total, se usa Avance % como aproximación. Observe cómo entidades con mayor tamaño presupuestal (PIM) no necesariamente lideran si su eficiencia de ejecución (Avance %) es menor.
''')

with tabs[1]:
    st.subheader("Variaciones presupuestales")
    if col_pia and col_pim:
        sample_list = data[ent_name].dropna().astype(str).unique().tolist()[:2000]
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
        st.markdown('''
**Qué mirar:** Cambios de PIA a PIM reflejan modificaciones presupuestarias. El indicador Crec_PIM_vs_PIA_% ayuda a identificar dónde creció o disminuyó el presupuesto relativo.
''')
        show_cols = [c for c in [ent_name, col_pia, col_pim, "Crec_PIM_vs_PIA_%", "PIM_per_cápita"] if c in data.columns]
        if show_cols:
            st.dataframe(data[show_cols].head(1000))
    else:
        st.info("No se detectaron columnas claramente identificables como PIA y PIM. Revise los encabezados del archivo.")

with tabs[2]:
    st.subheader("Eficiencia vs Tamaño")
    if col_avance and col_pim:
        base = data.dropna(subset=[col_avance, col_pim]).copy()
        if col_poblacion:
            size_enc = alt.Size(f"{col_poblacion}:Q", title="Población", scale=alt.Scale(range=[30, 400]))
            tooltip = [ent_name, alt.Tooltip(f"{col_avance}:Q", title="Avance %", format=".1f"),
                       alt.Tooltip(f"{col_pim}:Q", title="PIM", format=",.0f"),
                       alt.Tooltip(f"{col_poblacion}:Q", title="Población", format=",.0f")]
        else:
            size_enc = alt.value(80)
            tooltip = [ent_name, alt.Tooltip(f"{col_avance}:Q", title="Avance %", format=".1f"),
                       alt.Tooltip(f"{col_pim}:Q", title="PIM", format=",.0f")]
        if col_tipo:
            color_enc = alt.Color(f"{col_tipo}:N", title=to_title(col_tipo))
        else:
            color_enc = alt.value("#1f77b4")
        scatter = alt.Chart(base).mark_circle(opacity=0.7).encode(
            x=alt.X(f"{col_pim}:Q", title="PIM (Soles)", scale=alt.Scale(zero=False)),
            y=alt.Y(f"{col_avance}:Q", title="Avance %", scale=alt.Scale(domain=[0, 110])),
            color=color_enc,
            size=size_enc,
            tooltip=tooltip
        ).properties(height=500)
        st.altair_chart(scatter, use_container_width=True)
        st.markdown('''
**Lectura sugerida:** Cada punto es una entidad. El eje X muestra el tamaño presupuestal (PIM), el eje Y la eficiencia de ejecución (Avance %) y el tamaño del punto (si disponible) representa Población. Busque outliers: presupuestos grandes con bajo avance o presupuestos pequeños con alta eficiencia.
''')
    else:
        st.info("Faltan columnas para construir la comparación (Avance % y/o PIM).")

with tabs[3]:
    st.subheader("Tabla exploratoria (sin repetir métricas mostradas en gráficos)")
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
    st.markdown('''
**Nota:** Esta tabla resume variables complementarias a los gráficos, evitando repetir exactamente las mismas vistas. Úsela para explorar posiciones (Orden presupuestal), contexto poblacional y métricas derivadas como PIM per cápita y crecimiento relativo PIM/PIA.
''')

st.markdown("---")
with st.expander("ℹ️ Glosario PPR 0101 (2021)"):
    st.markdown('''
- **Propósito principal:** Evaluar programación y cumplimiento del presupuesto PPR 0101 (2021) para incrementar la práctica de actividades físicas, deportivas y recreativas.  
- **Entidades evaluadas:** Gobiernos locales (municipalidades) y gobiernos regionales.  
- **Fuentes:** DNCTD (base); Transparencia Económica - Consulta Amigable (PIA, PIM, Avance % y puntajes); INEI (población 2019).  
- **PIA:** Presupuesto Inicial de Apertura aprobado por el Titular.  
- **PIM:** Presupuesto Institucional Modificado tras incorporaciones y modificaciones.  
- **Total (puntaje):** Suma de puntajes por PIM, Avance % y Población.  
- **Avance %:** Ejecución de ingresos (Recaudado) y gastos (Compromiso/Devengado/Girado).  
- **Población:** Variable para ponderar/ contextualizar el impacto.  
- **Orden presupuestal:** Ranking según desempeño en ejecución y cumplimiento.
''')
st.success("✅ Listo. Use los filtros para descubrir historias en los datos. Guarde este repo en GitHub y despliegue en Streamlit Community Cloud.")
