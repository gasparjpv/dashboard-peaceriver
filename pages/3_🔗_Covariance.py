import pandas as pd
import streamlit as st
from sklearn.preprocessing import StandardScaler

# Carregar os dados do session_state
df = st.session_state['df']
gdf_points = st.session_state["gdf_points"]

# Carrega o CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Função para gerar tabela HTML de covariância sem negrito nos valores altos
def generate_html_table_covariance(df):
    html = "<table class='covariance-table'>"
    # Adiciona cabeçalho com espaço extra para a coluna de índice
    html += "<tr><th></th>" + "".join([f"<th>{col}</th>" for col in df.columns]) + "</tr>"
    # Adiciona cada linha com o índice na primeira coluna
    for idx, row in df.iterrows():
        html += f"<tr><th>{idx}</th>"
        for val in row:
            html += f"<td>{val:.2f}</td>"
        html += "</tr>"
    html += "</table>"
    return html

# Filtros
if len(st.session_state.bacias_selecionadas) == 0 or len(st.session_state.regioes_selecionadas) == 0:
    st.warning(
        "No basin or region was selected. Please select at least one to view the data."
    )
else:
    # Filtrar os dados com base nos anos selecionados, nas bacias e nas regiões selecionadas
    df_filtrado = gdf_points[
        (gdf_points["year"].isin(st.session_state.anos_selecionados))  # Filtro para anos selecionados
        & (gdf_points["basin_name"].isin(st.session_state.bacias_selecionadas))
        & (gdf_points["county_name"].isin(st.session_state.regioes_selecionadas))
    ]

    # Criação do pivot table para organizar os dados
    df_pivot = df_filtrado.pivot_table(index="activity_start_date", columns="analyte_primary_name", values="final_result_value")

    # Padroniza os dados antes de calcular a covariância
    scaler = StandardScaler()
    df_pivot_standardized = pd.DataFrame(scaler.fit_transform(df_pivot), columns=df_pivot.columns, index=df_pivot.index)

    # Calcula a matriz de covariância com os dados padronizados
    covariance_matrix_standardized = df_pivot_standardized.cov()

    # Exibição da matriz de covariância sem valores em negrito
    st.write("### Covariance Matrix between Analytes (Standardized)")
    html_table_covariance = generate_html_table_covariance(covariance_matrix_standardized)
    st.markdown(html_table_covariance, unsafe_allow_html=True)
