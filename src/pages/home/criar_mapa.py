import folium

from services.veiculos_service import VeiculoService

veiculo_service = VeiculoService()

def criar_mapa(latitude: float, longitude: float, raio_km: float, geolog: list):

    mapa = folium.Map(
        location=[latitude, longitude],
        zoom_start=12,
        control_scale=True,
    )

    folium.Marker(
        location=[latitude, longitude],
        tooltip="Ponto de referência",
        popup=folium.Popup(
            "<b>Ponto de referência</b>",
            max_width=300,
        ),
        icon=folium.Icon(
            color="red",
            icon="home",
        ),
    ).add_to(mapa)

    folium.Circle(
        location=[latitude, longitude],
        radius=raio_km * 1000,
        tooltip=f"Raio de busca: {raio_km:.1f} km",
        popup=(
            f"<b>Raio de busca</b><br>"
            f"{raio_km:.1f} km"
        ),
        color="blue",
        fill=True,
        fill_opacity=0.15,
    ).add_to(mapa)

    for telemetria in geolog:
        localizacao = telemetria.get("location")
        if not localizacao:
            continue

        coordenadas = localizacao.get("coordinates")
        if not coordenadas or len(coordenadas) != 2:
            continue

        longitude_veiculo = coordenadas[0]
        latitude_veiculo = coordenadas[1]

        distancia = telemetria.get("distancia_metros")
        if distancia is not None:
            distancia_km = distancia / 1000
            distancia_texto = f"{distancia_km:.2f} km"
        else:
            distancia_texto = "Não calculada"

        veiculo = veiculo_service.get_veiculo_by_id(telemetria.get("veiculo_id", 0))

        placa = veiculo.get("placa", "Não informado")
        modelo = veiculo.get("modelo", "Não informado")
        status = veiculo.get("status", "Não informado")

        popup_html = f"""
            <div style="width: 220px">
                <h4>Veículo</h4>
                <b>Placa:</b> {placa}<br>
                <b>Modelo:</b> {modelo}<br>
                <b>Status:</b> {status}<br>
                <b>Distância:</b> {distancia_texto}
            </div>
        """

        folium.Marker(
            location=[latitude_veiculo, longitude_veiculo],
            tooltip=placa,
            popup=folium.Popup(
                popup_html,
                max_width=300,
            ),
            icon=folium.Icon(
                color="green",
                icon="truck",
                prefix="fa",
            ),
        ).add_to(mapa)

    return mapa
