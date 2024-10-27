import sqlite3
import geopandas as gpd
import folium
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

# Definir layout da página como "wide" para ser responsivo
st.set_page_config(layout="wide")

# Título do Dashboard
st.title("Dashboard Peace River - Florida")

# Função para carregar o arquivo GeoPackage de HUC8
@st.cache_data
def carregar_geometria_huc8():
    return gpd.read_file("WBD HUC8.gpkg")

# Carregar a geometria HUC8
gdf_huc8 = carregar_geometria_huc8()

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

# Converter activity_start_date para datetime e extrair o ano
df["activity_start_date"] = pd.to_datetime(df["activity_start_date"], errors="coerce")
df["year"] = df["activity_start_date"].dt.year.astype("Int64")

# Criar um GeoDataFrame para os pontos do df
gdf_points = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df["x"], df["y"]), crs="EPSG:4326"
)

# === Filtros ===
ano_predefinido = (
    2024
    if 2024 in df["year"].unique()
    else sorted(df["year"].dropna().unique(), reverse=True)[0]
)

ano_selecionado = st.sidebar.selectbox(
    "Select the year for visualization",
    sorted(df["year"].dropna().unique(), reverse=True),
    index=list(sorted(df["year"].dropna().unique(), reverse=True)).index(ano_predefinido),
)

bacias_selecionadas = st.sidebar.multiselect(
    "Select the Watersheds",
    sorted(df["basin_name"].unique()),
    default=sorted(df["basin_name"].unique()),
)

regioes_selecionadas = st.sidebar.multiselect(
    "Select the Region",
    sorted(df["county_name"].unique()),
    default=sorted(df["county_name"].unique()),
)

# Selectbox para visualizar a geometria HUC8 e para aplicar o filtro HUC8
visualizar_huc8 = st.sidebar.checkbox("View HUC8 Geometry", value=False)

aplicar_filtro_huc8 = st.sidebar.checkbox("Apply HUC8 Filter to Points", value=False)


# Verificar se alguma bacia ou região foi selecionada
if len(bacias_selecionadas) == 0 or len(regioes_selecionadas) == 0:
    st.warning(
        "No watershed or region has been selected. Please select at least one to view the data."
    )
else:
    # Filtrar os dados com base no ano, nas bacias e nas regiões selecionadas
    df_filtrado = gdf_points[
        (gdf_points["year"] == ano_selecionado)
        & (gdf_points["basin_name"].isin(bacias_selecionadas))
        & (gdf_points["county_name"].isin(regioes_selecionadas))
    ]

    # Se a opção de aplicar o filtro por HUC8 estiver ativa, filtrar os pontos que estão dentro da geometria HUC8
    if aplicar_filtro_huc8 is True:
        df_filtrado = gpd.sjoin(df_filtrado, gdf_huc8, how="inner", predicate="within")

    if df_filtrado.empty:
        st.warning(
            f"No data available for the year {ano_selecionado}, in the selected watersheds and regions."
        )
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

        st.write("### Indicadores")

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
        if visualizar_huc8 is True and not gdf_huc8.empty:
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
