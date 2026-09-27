import streamlit as st

from pages.comum import (
    CONFIG_COLUNAS,
    SEM_LEITURA,
    botao_atualizar,
    carregar_visao_integrada,
    mostrar_falha,
    tabela_para_exibicao,
)

# Módulo 3: visão unificada (join poliglota em memória).

COLUNAS = [
    "motorista",
    "placa",
    "modelo",
    "status_motorista",
    "temperatura",
    "velocidade",
    "latitude",
    "longitude",
    "timestamp",
]

titulo, acao = st.columns([4, 1], vertical_alignment="bottom")
titulo.title("Visão Geral da Frota")
with acao:
    botao_atualizar()

st.write(
    "Cada linha junta o **cadastro do PostgreSQL** (motorista, placa, modelo e status) "
    "com a **última leitura de telemetria do MongoDB** (temperatura, velocidade e posição GeoJSON). "
    "Os dois bancos são cruzados em memória pelo identificador do veículo; nada é copiado de um para o outro."
)

try:
    visao = carregar_visao_integrada()
except Exception as erro:
    mostrar_falha(erro)
    st.stop()

if visao.empty:
    st.info("Nenhum veículo cadastrado no PostgreSQL. Rode o seed (`src/db/seed.py`).")
    st.stop()

st.dataframe(
    tabela_para_exibicao(visao, COLUNAS),
    hide_index=True,
    width="stretch",
    column_config=CONFIG_COLUNAS,
    placeholder=SEM_LEITURA,
)

sem_telemetria = visao.loc[visao["timestamp"].isna(), "placa"].tolist()
if sem_telemetria:
    st.info(
        "Sem telemetria registrada no MongoDB para: " + ", ".join(sem_telemetria)
        + ". Os dados de cadastro aparecem mesmo assim.",
        icon=":material/info:",
    )

st.caption(
    f"{len(visao)} veículos · Motorista, Placa, Modelo e Status vêm do PostgreSQL · "
    "Temperatura, Velocidade, Latitude, Longitude e Última Atualização vêm do MongoDB "
    "(passe o cursor sobre o nome da coluna)."
)
