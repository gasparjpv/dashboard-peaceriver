import pandas as pd
import streamlit as st

def highlight_high_correlation(val):
    """Destaca correlações altas em negrito"""
    color = "background-color: yellow" if abs(val) > 0.8 else ""
    return color
    
# Carregar os dados do session_state
if "df" not in st.session_state:
    st.error("The data was not loaded. Please return to the home page to load the data.")
    st.stop()
else:
    df = st.session_state["df"]


if "gdf_points" not in st.session_state:
    st.error("Geographic data was not loaded. Please return to the home page.")
    st.stop()
else:
    gdf_points = st.session_state["gdf_points"]

# Carrega o CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# Função para gerar tabela HTML com alta correlação em negrito e índice das linhas
def generate_html_table(df, threshold=0.7):
    html = "<table class='correlation-table'>"
    # Adiciona cabeçalho com espaço extra para a coluna de índice
    html += (
        "<tr><th></th>" + "".join([f"<th>{col}</th>" for col in df.columns]) + "</tr>"
    )
    # Adiciona cada linha com o índice na primeira coluna
    for idx, row in df.iterrows():
        html += f"<tr><th>{idx}</th>"
        for val in row:
            cell_class = "high-correlation" if abs(val) > threshold else ""
            html += f"<td class='{cell_class}'>{val:.2f}</td>"
        html += "</tr>"
    html += "</table>"
    return html


# Filtros
if (
    len(st.session_state.bacias_selecionadas) == 0
    or len(st.session_state.regioes_selecionadas) == 0
):
    st.warning(
        "No basin or region was selected. Please select at least one to view the data."
    )
else:
    # Filtrar os dados com base nos anos selecionados, nas bacias e nas regiões selecionadas
    df_filtrado = gdf_points[
        (
            gdf_points["year"].isin(st.session_state.anos_selecionados)
        )  # Usar lista de anos selecionados
        & (gdf_points["basin_name"].isin(st.session_state.bacias_selecionadas))
        & (gdf_points["county_name"].isin(st.session_state.regioes_selecionadas))
    ]

    # Caso você queira usar uma coluna de data ou outra categórica como índice, por exemplo, 'activity_start_date'
    df_pivot = df_filtrado.pivot_table(
        index="activity_start_date",
        columns="analyte_primary_name",
        values="final_result_value",
    )

    # Calcular a matriz de correlação entre os analitos
    correlation_matrix = df_pivot.corr()

    # Define uma função para aplicar estilo de negrito aos valores de alta correlação
    def highlight_high_correlation(val):
        return "font-weight: bold" if abs(val) > 0.7 else ""

    # Aplicar estilo e formatação
    correlation_matrix_formatted = (
        correlation_matrix.style.format("{:.2f}")  # Formatar para duas casas decimais
        .applymap(highlight_high_correlation)  # Aplicar a formatação célula por célula
)
    # Exibe o DataFrame estilizado no Streamlit com altura personalizada
    st.write("### Correlation Matrix between Analytes")
    html_table = generate_html_table(correlation_matrix)
    st.markdown(html_table, unsafe_allow_html=True)
