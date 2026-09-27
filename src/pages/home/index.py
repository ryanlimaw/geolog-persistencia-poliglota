import streamlit as st
from streamlit_folium import st_folium
from services.telemetria_service import TelemetriaService
from pages.home.criar_mapa import criar_mapa
from geopy.geocoders import Nominatim

telemetria_service = TelemetriaService()
geolocalizador = Nominatim(user_agent="geolog")

MODOS_DE_BUSCA = ["Veículos dentro do raio", "Veículos mais próximos"]

# Os campos lembram a última busca: ao sair da página e voltar, o Streamlit
# apaga o estado dos widgets, e sem isso a latitude/longitude voltavam a 0 e
# "Simular Movimentação" não conseguia refazer a consulta nem redesenhar o mapa.
anterior = st.session_state.get("ultima_busca", {})
st.session_state.setdefault("home_latitude", float(anterior.get("latitude", 0.0)))
st.session_state.setdefault("home_longitude", float(anterior.get("longitude", 0.0)))
st.session_state.setdefault("home_raio_km", float(anterior.get("raio_km", 10.0)))
st.session_state.setdefault("home_tipo_consulta", anterior.get("tipo_consulta", MODOS_DE_BUSCA[0]))

latitude = st.number_input("Latitude", format="%.6f", key="home_latitude")
longitude = st.number_input("Longitude", format="%.6f", key="home_longitude")
raio_km = st.number_input("Raio de busca (km)", min_value=0.1, max_value=500.0, step=1.0, key="home_raio_km")
tipo_consulta = st.radio(
    "Modo de busca",
    MODOS_DE_BUSCA,
    horizontal=True,
    help="Escolha entre listar a área encontrada ou ordenar os veículos pela distância.",
    key="home_tipo_consulta",
)

if tipo_consulta == "Veículos dentro do raio":
    st.caption("Mostra todos os veículos dentro da área. A ordem não representa distância.")
else:
    st.caption("Ordena os veículos do mais próximo ao mais distante e calcula a distância.")

col_buscar, col_simular = st.columns(2)
with col_buscar:
    buscar_veiculos = st.button(
        "Buscar veículos", 
        icon=":material/search:",
        type="primary", 
        help="Realiza a busca pelos veículos na área especificada.",
        use_container_width=True)
with col_simular:
    simular_movimentacao = st.button(
        "Simular Movimentação",
        icon=":material/directions_car:",
        use_container_width=True,
        help="Gera uma nova leitura GPS para cada veículo e atualiza os dados.",
    )

if buscar_veiculos or simular_movimentacao:
    if buscar_veiculos and latitude == 0 and longitude == 0:
        st.warning("Informe a latitude e a longitude do ponto de referência.")
        st.stop()

    try:
        with st.spinner("Carregando telemetria..."):
            if simular_movimentacao:
                quantidade = telemetria_service.simular_movimentacao()
                st.cache_data.clear()
                st.toast(f"{quantidade} veículo(s) movimentado(s).", icon=":material/directions_car:")

            if latitude == 0 and longitude == 0:
                st.info("Informe um ponto de referência para atualizar o mapa.")
                st.stop()

            if tipo_consulta == "Veículos dentro do raio":
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
            "tipo_consulta": tipo_consulta,
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

    tipo_consulta = busca.get("tipo_consulta", "Veículos dentro do raio")
    veiculos = busca["veiculos"]
    distancias = [
        veiculo["distancia_metros"]
        for veiculo in veiculos
        if veiculo.get("distancia_metros") is not None
    ]

    st.subheader(tipo_consulta)
    if tipo_consulta == "Veículos dentro do raio":
        st.info(f"{len(veiculos)} veículo(s) encontrado(s) dentro de {busca['raio_km']:.1f} km.")
    else:
        menor_distancia = min(distancias) / 1000 if distancias else None
        st.info(
            f"{len(veiculos)} veículo(s) encontrado(s), ordenados por proximidade."
            + (f" Mais próximo: {menor_distancia:.2f} km." if menor_distancia is not None else "")
        )

    _, kpi_veiculos, kpi_raio, _ = st.columns([1, 2, 2, 1])
    kpi_veiculos.metric(
        "Veículos encontrados",
        len(veiculos),
        icon=":material/local_shipping:",
        help="Quantidade de veículos dentro do raio informado.",
        border=True,
    )
    kpi_raio.metric(
        "Raio da busca",
        f"{busca['raio_km']:.1f} km",
        icon=":material/radar:",
        help="Distância máxima considerada a partir do ponto de referência.",
        border=True,
    )

    if tipo_consulta == "Veículos mais próximos":
        linhas = [
            {
                "Ordem": indice,
                "Veículo": veiculo.get("veiculo_id", "Não informado"),
                "Distância": f"{veiculo['distancia_metros'] / 1000:.2f} km",
            }
            for indice, veiculo in enumerate(veiculos, start=1)
            if veiculo.get("distancia_metros") is not None
        ]
        st.dataframe(linhas, hide_index=True, use_container_width=True)
        st.caption("A lista representa apenas os veículos contidos no círculo.")

    st.subheader("Mapa da telemetria")
    st.caption(
        "Cada ponto representa a última leitura de telemetria de um veículo. "
        + "Clique no ponto para ver os detalhes (placa, modelo, status, temperatura, velocidade e horário)."
    )

    st_folium(mapa, width=2000, height=700, key="mapa_telemetria")
