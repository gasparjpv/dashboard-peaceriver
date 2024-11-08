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

# Definir layout da página como "wide" para ser responsivo
st.set_page_config(layout="wide")

# Carregar o CSS imagem unicamp
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Carregar a imagem
logo = Image.open("imagens/unicamp.jpg")

# Converter a imagem para Base64
buffered = io.BytesIO()
logo.save(buffered, format="PNG")
logo_base64 = base64.b64encode(buffered.getvalue()).decode()

# Renderizar a imagem com a classe CSS personalizada
st.markdown(
    f'<img src="data:image/png;base64,{logo_base64}" class="header-logo">',
    unsafe_allow_html=True
)

# Carregar o CSS
with open("styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)



# Carregar a imagem para o topo da página
top_image = Image.open("imagens/ft.jpg")  # Substitua pelo caminho correto

# Converter a imagem para Base64
buffered = io.BytesIO()
top_image.save(buffered, format="PNG")
top_image_base64 = base64.b64encode(buffered.getvalue()).decode()

# Renderizar a imagem no topo da página com a nova classe CSS
st.markdown(
    f'<img src="data:image/png;base64,{top_image_base64}" class="top-logo">',
    unsafe_allow_html=True
)

# Título do Dashboard, alinhado à direita
st.markdown("<h1 class='title-right'>Peace River - Florida</h1>", unsafe_allow_html=True)



# Função para carregar o arquivo CSS
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Carregar o arquivo styles.css
load_css("styles.css")

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

# Criar um GeoDataFrame para os pontos do df
gdf_points = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df["x"], df["y"]), crs="EPSG:4326"
)

st.session_state["gdf_points"] = gdf_points

# === Filtros ===

# Inicializar os filtros no `session_state` se não existirem
if "anos_selecionados" not in st.session_state:
    st.session_state.anos_selecionados = [2024]  # Ano padrão

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
        numero_total_organization_name = len(df_filtrado["organization_name"].unique())
        numero_total_basin_name = len(df_filtrado["basin_name"].unique())
        numero_total_result_key = len(df_filtrado["result_key"].unique())

        st.write("### KPIs")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Analytes", numero_total_analitos)
            st.metric("Total Regions", numero_total_county_name)
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
            ["analyte_primary_name"]  # colocar dentro das chaves retar caso queira apresentar unidade, "dep_result_unit"
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
            CV=lambda x: x.std() / x.mean() * 100,
            Q1=lambda x: x.quantile(0.25),
            Q2=lambda x: x.quantile(0.5),
            Q3=lambda x: x.quantile(0.75),
            Skewness=lambda x: stats.skew(x, nan_policy='omit'),
            Kurtosis=lambda x: stats.kurtosis(x, nan_policy='omit')
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

        if not df_hist.empty:
            st.write(
                f"**Histogram of 'final_result_value' for the analyte {analyte_selecionado}**"
            )

            hist_values, bin_edges = np.histogram(
                df_hist["final_result_value"].dropna(), bins=20
            )
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
