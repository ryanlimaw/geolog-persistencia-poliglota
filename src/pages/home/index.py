import streamlit as st
from streamlit_folium import st_folium
from services.telemetria_service import TelemetriaService
from pages.home.criar_mapa import criar_mapa
from geopy.geocoders import Nominatim

telemetria_service = TelemetriaService()
geolocalizador = Nominatim(user_agent="geolog")

col1, col2 = st.columns(2)
latitude = None
longitude = None

tipo_consulta = st.radio( "Tipo de consulta MongoDB", [ "Área Delimitada (Raio)", "Locais Próximos" ], horizontal=True)

with col1: 
    endereco = st.text_input( "Endereço", placeholder="Digite o endereço para buscar latitude e longitude")
    latitude = st.number_input( "Latitude", format="%.6f", disabled=(endereco != "")) 
    
with col2: 
    raio_km = st.number_input( "Raio de busca (km)", min_value=0.1, max_value=500.0, value=10.0, step=1.0)
    longitude = st.number_input( "Longitude", format="%.6f", disabled=(endereco != "")) 

if st.button( "Buscar veículos", type="primary", use_container_width=True ):
    if endereco:
        try:
            localizacao = geolocalizador.geocode(endereco)
            if localizacao:
                latitude = localizacao.latitude
                longitude = localizacao.longitude
            else:
                st.error("Endereço não encontrado. Por favor, verifique e tente novamente.")
                st.stop()
        except Exception as erro:
            st.error("Erro ao buscar o endereço.")
            st.exception(erro)
            st.stop()

    # 0,0 é o valor inicial dos campos (e fica no oceano): sem endereço nem
    # coordenadas preenchidas, não há o que buscar.
    if latitude == 0 and longitude == 0:
        st.warning("Informe um endereço ou a latitude e a longitude do ponto de referência.")
        st.stop()

    try:
        with st.spinner("Carregando telemetria..."):
            if tipo_consulta == "Área Delimitada (Raio)":
                # $geoWithin + $centerSphere: quem está dentro do círculo.
                veiculos = telemetria_service.buscar_veiculos_proximos(latitude, longitude, raio_km)
            else:
                # $geoNear: os mais próximos primeiro, com a distância até o ponto.
                veiculos = telemetria_service.buscar_veiculos_e_distancia(latitude, longitude, raio_km)

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
    try:
        mapa = criar_mapa(
            busca["latitude"],
            busca["longitude"],
            busca["raio_km"],
            busca["veiculos"],
        )
    except Exception as erro:
        st.error("Não foi possível consultar o PostgreSQL (placa, modelo e status dos veículos do mapa).")
        st.exception(erro)
        st.stop()
    st_folium(mapa, width=700, height=500, key="mapa_telemetria")
