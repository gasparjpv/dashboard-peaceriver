import sqlite3
import geopandas as gpd
import folium
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import scipy.stats as stats
from PIL import Image
import base64
import io

# Funções seguras para calcular Skewness e Kurtosis
def safe_skew(x):
    if len(x) < 2 or np.std(x) < 1e-10:  # Verifica se há dados suficientes e variabilidade
        return np.nan
    return stats.skew(x, nan_policy='omit')

def safe_kurtosis(x):
    if len(x) < 2 or np.std(x) < 1e-10:  # Verifica se há dados suficientes e variabilidade
        return np.nan
    return stats.kurtosis(x, nan_policy='omit')



# Calcular o número de bins de forma responsiva usando a regra de Freedman-Diaconis
def calcular_bins(data):
    if len(data) < 2:  # Caso haja poucos dados, usar apenas 1 bin
        return 1
    iqr = np.percentile(data, 75) - np.percentile(data, 25)  # Intervalo interquartil
    bin_width = 2 * iqr / len(data) ** (1 / 3)  # Largura do bin pela regra de Freedman-Diaconis
    num_bins = max(1, int((data.max() - data.min()) / bin_width))  # Garantir ao menos 1 bin
    return num_bins

# Configuração da página
st.set_page_config(layout="wide")

# Função para carregar e converter imagens para Base64
def convert_image_to_base64(image_path):
    image = Image.open(image_path)
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# Converter imagens para Base64
logo_base64 = convert_image_to_base64("imagens/unicamp.jpg")
top_image_base64 = convert_image_to_base64("imagens/ft.jpg")

# Renderizar o cabeçalho
st.markdown(
    f"""
    <div class="header-container">
        <img src="data:image/png;base64,{top_image_base64}" class="top-logo">
        <div class="title-right">Peace River - Florida</div>
        <img src="data:image/png;base64,{logo_base64}" class="header-logo">
    </div>
    """,
    unsafe_allow_html=True,
)

# Carregar o CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Função para carregar o arquivo GeoPackage de HUC8
@st.cache_data
def carregar_geometria_huc8():
    return gpd.read_file("WBD HUC8.gpkg")

# Carregar a geometria HUC8
gdf_huc8 = carregar_geometria_huc8()
st.session_state["gdf_huc8"] = gdf_huc8

# Função para carregar dados do banco de dados SQLite
@st.cache_data
def carregar_dados_sqlite():
    conn = sqlite3.connect("banco_dados.db")
    query = "SELECT * FROM minha_tabela"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# Carregar os dados do banco de dados SQLite
df = carregar_dados_sqlite()

# Definir colunas que devem ser convertidas para float e string
colunas_float = ["x", "y", "final_result_value"]
colunas_string = [
    "analyte_primary_name",
    "monitoring_location_name",
    "basin_name",
    "county_name",
    "dep_result_unit",
]

# Converter as colunas especificadas para float
for coluna in colunas_float:
    df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

# Converter as colunas especificadas para string
for coluna in colunas_string:
    df[coluna] = df[coluna].astype(str)

# Passar dados para página 2
st.session_state["df"] = df

# Converter activity_start_date para datetime e extrair o ano
df["activity_start_date"] = pd.to_datetime(df["activity_start_date"], errors="coerce")
df["year"] = df["activity_start_date"].dt.year.astype("Int64")
df["month"] = df["activity_start_date"].dt.month.astype("Int64")

# Criar um GeoDataFrame para os pontos do df
gdf_points = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df["x"], df["y"]), crs="EPSG:4326"
)

st.session_state["gdf_points"] = gdf_points

# === Filtros ===

# Inicializar os filtros no `session_state` se não existirem
if "anos_selecionados" not in st.session_state:
    st.session_state.anos_selecionados = [2023]  # Ano padrão

if "mes_selecionados" not in st.session_state:
    st.session_state.mes_selecionados = sorted(df["month"].unique(), reverse=True) # Mes padrão

if "bacias_selecionadas" not in st.session_state:
    st.session_state.bacias_selecionadas = sorted(df["basin_name"].unique())

if "regioes_selecionadas" not in st.session_state:
    st.session_state.regioes_selecionadas = sorted(df["county_name"].unique())

if "visualizar_huc8" not in st.session_state:
    st.session_state.visualizar_huc8 = False

if "aplicar_filtro_huc8" not in st.session_state:
    st.session_state.aplicar_filtro_huc8 = False

# Multiselect para anos, bacias e regiões, com armazenamento de filtro no session_state
anos_selecionados = st.sidebar.multiselect(
    "Select the years for visualization",
    sorted(df["year"].dropna().unique(), reverse=True),
    default=st.session_state.anos_selecionados
)

mes_selecionados = st.sidebar.multiselect(
    "Select the month for visualization",
    sorted(df["month"].dropna().unique(), reverse=True),
    default=st.session_state.mes_selecionados
)

bacias_selecionadas = st.sidebar.multiselect(
    "Select the Watersheds",
    sorted(df["basin_name"].unique()),
    default=st.session_state.bacias_selecionadas
)

regioes_selecionadas = st.sidebar.multiselect(
    "Select the Region",
    sorted(df["county_name"].unique()),
    default=st.session_state.regioes_selecionadas
)

visualizar_huc8 = st.sidebar.checkbox("View HUC8 Geometry", value=st.session_state.visualizar_huc8)
aplicar_filtro_huc8 = st.sidebar.checkbox("Apply HUC8 to Points", value=st.session_state.aplicar_filtro_huc8)

# Atualizar session_state apenas se o valor tiver mudado
if anos_selecionados != st.session_state.anos_selecionados:
    st.session_state.anos_selecionados = anos_selecionados

if mes_selecionados != st.session_state.mes_selecionados:
    st.session_state.mes_selecionados = mes_selecionados

if bacias_selecionadas != st.session_state.bacias_selecionadas:
    st.session_state.bacias_selecionadas = bacias_selecionadas

if regioes_selecionadas != st.session_state.regioes_selecionadas:
    st.session_state.regioes_selecionadas = regioes_selecionadas

if visualizar_huc8 != st.session_state.visualizar_huc8:
    st.session_state.visualizar_huc8 = visualizar_huc8

if aplicar_filtro_huc8 != st.session_state.aplicar_filtro_huc8:
    st.session_state.aplicar_filtro_huc8 = aplicar_filtro_huc8

# Filtrar os dados com base nos filtros selecionados
if len(st.session_state.bacias_selecionadas) == 0 or len(st.session_state.regioes_selecionadas) == 0:
    st.warning("No watershed or region has been selected. Please select at least one to view the data.")
else:
    df_filtrado = gdf_points[
        (gdf_points["year"].isin(st.session_state.anos_selecionados))
        & (gdf_points["month"].isin(st.session_state.mes_selecionados))
        & (gdf_points["basin_name"].isin(st.session_state.bacias_selecionadas))
        & (gdf_points["county_name"].isin(st.session_state.regioes_selecionadas))
    ]

    # Aplicar filtro de HUC8 se a opção estiver marcada
    if st.session_state.aplicar_filtro_huc8:
        df_filtrado = gpd.sjoin(df_filtrado, gdf_huc8, how="inner", predicate="within")

    if df_filtrado.empty:
        st.warning("No data available for the selected criteria.")
    else:
        # === KPIs ===
        numero_total_analitos = len(df_filtrado["analyte_primary_name"].unique())
        numero_total_county_name = len(df_filtrado["county_name"].unique())
        numero_total_monitoring_location_name = len(
            df_filtrado["monitoring_location_name"].unique()
        )
        total_number_above_20 = df_filtrado[
                    (df_filtrado["analyte_primary_name"] == "Chlorophyll a- corrected") &
                    (df_filtrado["final_result_value"] > 20)
                ]["monitoring_location_name"].nunique()
        numero_total_organization_name = len(df_filtrado["organization_name"].unique())
        numero_total_basin_name = len(df_filtrado["basin_name"].unique())
        numero_total_result_key = len(df_filtrado["result_key"].unique())

        st.write("### KPIs")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Analytes", numero_total_analitos)
            st.metric("Total Regions", numero_total_county_name)
            st.metric("Total locations with Chlorophyll a- corrected > 20", total_number_above_20)
        with col2:
            st.metric("Total Locations", numero_total_monitoring_location_name)
            st.metric("Total Organizations", numero_total_organization_name)
        with col3:
            st.metric("Total Watersheds", numero_total_basin_name)
            st.metric("Total Results", numero_total_result_key)
        
        # === Resumo Estatístico por Analito (vinculado aos filtros) ===
        st.write("### Statistical Summary by Analyte")

        # Gerar a análise estatística para cada analito e sua respectiva unidade de medida (dep_result_unit)
        resumo_estatistico = df_filtrado.groupby(
            ["analyte_primary_name"]
        )["final_result_value"].agg(
            Min=('min'),
            Max=('max'),
            Mean=('mean'),
            Median=('median'),
            Midpoint=lambda x: (x.min() + x.max()) / 2,
            Range=lambda x: x.max() - x.min(),
            IQR=lambda x: x.quantile(0.75) - x.quantile(0.25),
            SIQR=lambda x: (x.quantile(0.75) - x.quantile(0.25)) / 2,
            Variance=('var'),
            Std=('std'),
            CV=lambda x: x.std() / x.mean() * 100 if x.mean() != 0 else np.nan,
            Q1=lambda x: x.quantile(0.25),
            Q2=lambda x: x.quantile(0.5),
            Q3=lambda x: x.quantile(0.75),
            Skewness=lambda x: safe_skew(x),
            Kurtosis=lambda x: safe_kurtosis(x)
        )

        # Exibir a tabela com alinhamento à esquerda e responsividade
        styled_summary_table = resumo_estatistico.style.format("{:.2f}").set_table_attributes('class="styled-table"')

  
        # Renderizar a tabela no Streamlit
        st.write(styled_summary_table.to_html(), unsafe_allow_html=True)

        # === Filtro para analitos no histograma ===
        if "Chlorophyll a- corrected" in df_filtrado["analyte_primary_name"].unique():
            analito_predefinido = "Chlorophyll a- corrected"
        else:
            analito_predefinido = df_filtrado["analyte_primary_name"].unique()[0]

        analyte_selecionado = st.selectbox(
            "**Select the analyte type to view the histogram**",
            sorted(df_filtrado["analyte_primary_name"].unique()),
            index=list(sorted(df_filtrado["analyte_primary_name"].unique())).index(analito_predefinido)
        )

        df_hist = df_filtrado[
            df_filtrado["analyte_primary_name"] == analyte_selecionado
        ]
        filtered_values = df_hist["final_result_value"].dropna()
        num_bins = calcular_bins(filtered_values)
        
        if not df_hist.empty:
            st.write(
                f"**Histogram of 'final_result_value' for the analyte {analyte_selecionado}**"
            )
            st.write("Bin number according to Freedman-Diaconis rule")
            
            #hist_values, bin_edges = np.histogram(
            #    df_hist["final_result_value"].dropna(), bins=40
            #)
            
            hist_values, bin_edges = np.histogram(filtered_values, bins=num_bins)
            
            bin_edges = np.round(bin_edges, decimals=2)

            hist_df = pd.DataFrame({"bin_edges": bin_edges[:-1], "counts": hist_values})
            hist_df = hist_df.sort_values(by="bin_edges")

            st.bar_chart(hist_df.set_index("bin_edges"))
        else:
            st.write("No data available for the selected analyte.")

        # === Mapa ===
        df_mapa = (
            df_filtrado[
                df_filtrado["analyte_primary_name"] == "Chlorophyll a- corrected"
            ]
            .groupby("monitoring_location_name", as_index=False)
            .agg({"final_result_value": "max", "x": "first", "y": "first"})
        )

        # Verificar se o mapa já foi renderizado antes para manter o centro e o zoom
        if 'centro_mapa' not in st.session_state:
            st.session_state['centro_mapa'] = [df_mapa["y"].mean(), df_mapa["x"].mean()]
            st.session_state['zoom'] = 10

        # Criar o mapa usando as coordenadas do centro e zoom armazenadas
        mapa = folium.Map(location=st.session_state['centro_mapa'], zoom_start=st.session_state['zoom'])
        # Adicionar as geometrias HUC8 ao mapa usando GeoJson se selecionado para visualização
        if st.session_state.visualizar_huc8 is True and not gdf_huc8.empty:
            folium.GeoJson(
                gdf_huc8[['geometry', 'huc8']],
                name="HUC8 Regions",
                tooltip=folium.GeoJsonTooltip(fields=['huc8'], aliases=['HUC8:']),
                style_function=lambda x: {'color': 'blue', 'weight': 0.5}
            ).add_to(mapa)

        # Adicionar os pontos de monitoramento ao mapa
        for _, row in df_mapa.iterrows():
            color = "red" if row["final_result_value"] > 20 else "blue"
            folium.Marker(
                location=[row["y"], row["x"]],
                popup=row["monitoring_location_name"],
                icon=folium.Icon(color=color),
            ).add_to(mapa)

        # Adicionar controle de camadas ao mapa para alternar entre as camadas
        folium.LayerControl().add_to(mapa)

        # Exibir o mapa no Streamlit
        st_folium(mapa, width=1500, height=800)
        st.metric("Total locations with Chlorophyll - a corrected > 20", total_number_above_20)
