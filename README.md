
# Visualizador Ranking PPR 0101 – 2021

App de Streamlit para explorar el ranking del PPR 0101 (2021). Incluye gráficos comparativos y tabla de resumen, con texto explicativo sobre PIA, PIM, Avance %, Población, Total y Orden presupuestal.

## Cómo usar

1. **Descarga este repositorio** y súbelo a GitHub (o haz *Fork*).
2. Verifica que el archivo de datos esté en `data/PPR 0101-2021.xlsx` (puedes reemplazarlo por una versión actualizada manteniendo el nombre o ajusta `DATA_PATH` en `app.py`).
3. En tu entorno local, instala dependencias:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```
4. Para **Streamlit Community Cloud**:
   - Crea una app nueva apuntando a tu repo.
   - Archivo principal: `app.py`.
   - Python version: 3.11+.
   - Asegúrate de que `requirements.txt` esté en la raíz.

## Notas
- El app detecta columnas clave de forma robusta (por ejemplo, acepta `Avance`, `Avance %` o `Ejecución`).
- Incluye métricas derivadas: `PIM_per_cápita` y `Crec_PIM_vs_PIA_%`.
- No repite las mismas vistas entre gráficos y tabla: la tabla resalta variables complementarias.
