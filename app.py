import streamlit as st
import pandas as pd
from datetime import datetime, date
import sqlite3
import io
import matplotlib.pyplot as plt
from fpdf import FPDF
from wordcloud import WordCloud
import dateparser
import os

st.set_page_config(page_title="Explorador de Tesis Jurídicas", layout="wide")

# Logo desde GitHub
st.markdown("""
    <div style='text-align: right;'>
        <img src='https://raw.githubusercontent.com/marvr17/app_explorador_tesis_ultima_version/main/logo_dukaz.png' width='120'>
    </div>
""", unsafe_allow_html=True)

DB_PATH = "tesis_juridicas.db"

def extraer_año(texto):
    fecha = dateparser.parse(str(texto))
    if fecha:
        return fecha.year
    return None

@st.cache_data
def cargar_datos():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM tesis", conn)
    conn.close()
    df["año"] = df["fecha_publicacion"].apply(extraer_año)
    return df

df = cargar_datos()

st.markdown("## ⚖️ Explorador de Tesis Jurídicas")
st.markdown("Filtra, selecciona, compara y exporta tus tesis jurídicas de forma fácil y eficiente.")

tabs = st.tabs(["🔍 Exploración", "📊 Visualización", "📄 Comparativa / Exportación"])

# EXPLORACIÓN
tab_exploracion = tabs[0]
with tab_exploracion:
    st.markdown("### 📋 Todas las tesis disponibles")

    with st.expander("🔍 Filtros avanzados", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            query = st.text_input("🔎 Palabras clave", help="Puedes usar operadores como AND, OR, NOT")
            logica = st.radio("🔗 Lógica de búsqueda", ["AND", "OR"], horizontal=True)
        with col2:
            materias = st.multiselect("📚 Materias", sorted(df["materia"].dropna().unique().tolist()))
        with col3:
            instancias = st.multiselect("🏛️ Instancias", sorted(df["instancia"].dropna().unique().tolist()))
        with col4:
            tipos = st.multiselect("📌 Tipos de tesis", sorted(df["tipo"].dropna().unique().tolist()))

        col5, col6 = st.columns(2)
        with col5:
            if df["año"].notna().any():
                min_year = int(df["año"].min())
                max_year = int(df["año"].max())
            else:
                min_year = 2000
                max_year = datetime.now().year
            rango_anios = st.slider("📅 Rango de años", min_year, max_year, (min_year, max_year))
        with col6:
            orden = st.selectbox("↕️ Ordenar por", ["Año (desc)", "Año (asc)", "Materia", "Tipo"])

        st.info("Puedes usar filtros combinados para afinar tu búsqueda. Por ejemplo: seleccionar un tipo de tesis, varias materias y una palabra clave usando lógica AND/OR.")

    filtro = df.copy()
    if query:
        if logica == "AND":
            palabras = [p.strip() for p in query.upper().split("AND")]
            for palabra in palabras:
                filtro = filtro[
                    filtro["texto_completo"].str.contains(palabra, case=False, na=False) |
                    filtro["rubro"].str.contains(palabra, case=False, na=False)
                ]
        elif logica == "OR":
            palabras = [p.strip() for p in query.upper().split("OR")]
            cond = pd.Series(False, index=filtro.index)
            for palabra in palabras:
                cond = cond | filtro["texto_completo"].str.contains(palabra, case=False, na=False) | \
                             filtro["rubro"].str.contains(palabra, case=False, na=False)
            filtro = filtro[cond]
    if materias:
        filtro = filtro[filtro["materia"].isin(materias)]
    if instancias:
        filtro = filtro[filtro["instancia"].isin(instancias)]
    if tipos:
        filtro = filtro[filtro["tipo"].isin(tipos)]

    filtro = filtro[(filtro["año"] >= rango_anios[0]) & (filtro["año"] <= rango_anios[1])]

    if orden == "Año (desc)":
        filtro = filtro.sort_values("año", ascending=False)
    elif orden == "Año (asc)":
        filtro = filtro.sort_values("año", ascending=True)
    elif orden == "Materia":
        filtro = filtro.sort_values("materia")
    elif orden == "Tipo":
        filtro = filtro.sort_values("tipo")

    st.markdown(f"### 📄 {len(filtro)} tesis encontradas.")
    st.dataframe(filtro[["registro_digital", "materia", "instancia", "tipo", "rubro"]], use_container_width=True)

# VISUALIZACIÓN
tab_visualizacion = tabs[1]
with tab_visualizacion:
    st.markdown("### 📊 Visualizaciones")
    if not filtro.empty:
        colv1, colv2 = st.columns(2)
        with colv1:
            tipo_counts = filtro["tipo"].value_counts()
            fig, ax = plt.subplots()
            tipo_counts.plot(kind='bar', ax=ax)
            ax.set_title("Cantidad por tipo de tesis")
            st.pyplot(fig)
        with colv2:
            materia_counts = filtro["materia"].value_counts().head(10)
            fig, ax = plt.subplots(figsize=(7, 7))
            materia_counts.plot(kind='pie', autopct='%1.1f%%', ax=ax)
            ax.set_ylabel("")
            ax.set_title("Top 10 materias")
            st.pyplot(fig)

        st.markdown("### ☁️ Wordcloud de Rubros")
        texto_rubros = " ".join(filtro["rubro"].dropna().astype(str))
        if texto_rubros:
            wc = WordCloud(width=800, height=400, background_color="white", max_words=80, contour_color='gray').generate(texto_rubros)
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wc, interpolation='bilinear')
            ax.axis("off")
            st.pyplot(fig)

# COMPARATIVA Y EXPORTACIÓN
tab_exportacion = tabs[2]
with tab_exportacion:
    st.markdown("### 📤 Comparar y Exportar Tesis")
    if not filtro.empty:
        editable_df = filtro[["registro_digital", "instancia", "materia", "tipo", "rubro", "fecha_publicacion"]].copy()
        editable_df.insert(0, "Seleccionar", False)
        seleccion = st.data_editor(editable_df, use_container_width=True, height=500, num_rows="dynamic")
        seleccionadas = seleccion[seleccion["Seleccionar"] == True]

        if not seleccionadas.empty:
            st.success(f"{len(seleccionadas)} tesis seleccionadas.")
            colx1, colx2 = st.columns(2)
            with colx1:
                excel_buffer = io.BytesIO()
                seleccionadas.drop(columns=["Seleccionar"], errors='ignore').to_excel(excel_buffer, index=False, engine="xlsxwriter")
                excel_buffer.seek(0)
                st.download_button("📥 Exportar seleccionadas a Excel", excel_buffer, file_name="tesis_seleccionadas.xlsx")

            with colx2:
                class PDF(FPDF):
                    def header(self):
                        self.set_font("Arial", "B", 12)
                        self.cell(0, 10, "Tesis Seleccionadas - DUKAZ", ln=True, align="C")
                        self.ln(5)

                    def add_portada(self):
                        self.add_page()
                        self.set_font("Arial", "B", 16)
                        self.ln(80)
                        self.cell(0, 10, "Explorador de Tesis Jurídicas", ln=True, align="C")
                        self.set_font("Arial", "", 12)
                        self.cell(0, 10, f"Fecha: {date.today().strftime('%d/%m/%Y')}", ln=True, align="C")
                        self.cell(0, 10, "Elaborado por: DUKAZ", ln=True, align="C")
                        self.ln(10)

                    def add_tesis(self, row, texto_completo):
                        self.set_font("Arial", "B", 10)
                        self.cell(0, 10, f"Tesis {row['registro_digital']}", ln=True)
                        self.set_font("Arial", "", 10)
                        self.multi_cell(0, 8, f"Rubro: {row['rubro']}")
                        self.cell(0, 8, f"Tipo: {row['tipo']} - Materia: {row['materia']} - Instancia: {row['instancia']} - Fecha: {row['fecha_publicacion']}", ln=True)
                        self.ln(2)
                        self.set_font("Arial", "I", 9)
                        self.multi_cell(0, 6, f"Texto completo:\n{texto_completo}")
                        self.ln(10)

                pdf = PDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                pdf.add_portada()
                pdf.add_page()
                for _, row in seleccionadas.iterrows():
                    texto_completo = filtro[filtro['registro_digital'] == row['registro_digital']].iloc[0]["texto_completo"]
                    pdf.add_tesis(row, texto_completo)
                pdf_bytes = pdf.output(dest='S').encode('latin1')
                st.download_button("📄 Exportar seleccionadas a PDF", data=pdf_bytes, file_name="tesis_seleccionadas.pdf")

            st.markdown("### 🔎 Comparativa de Tesis Seleccionadas")
            comparar_cols = ["registro_digital", "instancia", "materia", "tipo", "fecha_publicacion"]
            st.dataframe(seleccionadas[comparar_cols].reset_index(drop=True), use_container_width=True)
            for _, row in seleccionadas.iterrows():
                with st.expander(f"👁️ Tesis {row['registro_digital']} - {row['rubro'][:50]}..."):
                    st.markdown(f"**Instancia:** {row['instancia']}")
                    st.markdown(f"**Tipo:** {row['tipo']}")
                    st.markdown(f"**Materia:** {row['materia']}")
                    st.markdown(f"**Fecha publicación:** {row['fecha_publicacion']}")
                    st.text_area("Texto completo", filtro[filtro['registro_digital'] == row['registro_digital']].iloc[0]["texto_completo"], height=300)
    else:
        st.warning("No hay tesis disponibles para mostrar.")

st.markdown("---")
st.markdown("Made with ❤️ by **DUKAZ**")
