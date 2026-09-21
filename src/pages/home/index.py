import streamlit as st
from streamlit_folium import st_folium
from services.telemetria_service import TelemetriaService
from src.pages.home.criar_mapa import criar_mapa

telemetria_service = TelemetriaService()

col1, col2 = st.columns(2) 

with col1: 
    latitude = st.number_input( "Latitude", format="%.6f" ) 
    longitude = st.number_input( "Longitude", format="%.6f" ) 
    
with col2: 
    raio_km = st.number_input( "Raio de busca (km)", min_value=0.1, max_value=500.0, value=10.0, step=1.0)

tipo_consulta = st.radio( "Tipo de consulta MongoDB", [ "Área Delimitada", "Locais Próximos" ], horizontal=True)

if st.button( "Buscar veículos", type="primary", use_container_width=True ):

    try:
        with st.spinner("Carregando telemetria..."):
            if tipo_consulta == "Área Delimitada":
                veiculos = telemetria_service.buscar_veiculos_por_raio(latitude, longitude, raio_km)
            else:
                veiculos = telemetria_service.buscar_veiculos_proximos(latitude, longitude, raio_km)

        st.session_state["ultima_busca"] = {
            "latitude": latitude,
            "longitude": longitude,
            "raio_km": raio_km,
            "veiculos": veiculos,
        }

    except Exception as erro:
        st.error("Não foi possível conectar ao MongoDB ou consultar a telemetria.")
        st.exception(erro)

if "ultima_busca" in st.session_state:
    busca = st.session_state["ultima_busca"]
    mapa = criar_mapa(
        busca["latitude"],
        busca["longitude"],
        busca["raio_km"],
        busca["veiculos"],
    )
    st_folium(mapa, width=700, height=500, key="mapa_telemetria")
