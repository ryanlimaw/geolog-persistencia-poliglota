import pandas as pd
import streamlit as st

from pages.comum import (
    CONFIG_COLUNAS,
    SEM_LEITURA,
    botao_atualizar,
    carregar_historico_temperatura,
    carregar_indicadores,
    carregar_motoristas_por_status,
    carregar_visao_integrada,
    horario_local,
    mostrar_falha,
    numero_br,
    tabela_para_exibicao,
)
from pages.dashboard.graficos import (
    grafico_historico_temperatura,
    grafico_status_motoristas,
    grafico_velocidade_atual,
)
from services.frota_service import SITUACAO_PARADO, situacao_por_veiculo
from services.telemetria_service import LIMITE_VELOCIDADE

# Módulo 4: dashboard analítico.
# Ordem de leitura: os números (KPIs) → cada veículo agora → gráficos do
# estado atual → o histórico de temperatura.

titulo, acao = st.columns([4, 1], vertical_alignment="bottom")
titulo.title("Dashboard da Frota")
with acao:
    botao_atualizar()

try:
    indicadores = carregar_indicadores()
    visao = carregar_visao_integrada()
    historico = carregar_historico_temperatura()
    status = carregar_motoristas_por_status()
except Exception as erro:
    mostrar_falha(erro)
    st.stop()

situacao = situacao_por_veiculo(visao, historico, LIMITE_VELOCIDADE)

ultima_leitura = visao["timestamp"].max()
st.caption(
    "Estado atual pela **última leitura de cada veículo** · cadastro no PostgreSQL, telemetria no MongoDB"
    + (
        f" · leitura mais recente: {horario_local(pd.Series([ultima_leitura])).iloc[0]:%d/%m/%Y %H:%M} (Brasília)"
        if pd.notna(ultima_leitura)
        else ""
    )
)

# ============================================================
# KPIS
# ============================================================

temperatura_media = indicadores["temperatura_media"]
placas_paradas = situacao.loc[situacao["situacao"] == SITUACAO_PARADO, "placa"].tolist()
velocidade_por_placa = dict(zip(visao["placa"], visao["velocidade"]))
alertas_texto = ", ".join(
    f"{placa} a {velocidade_por_placa[placa]:.0f} km/h" for placa in indicadores["placas_em_alerta"]
)

kpi_frota, kpi_temperatura, kpi_alertas, kpi_parados = st.columns(4)

kpi_frota.metric(
    "Frota ativa",
    indicadores["frota_ativa"],
    delta=f"de {indicadores['frota_total']} veículos cadastrados",
    delta_color="off",
    delta_arrow="off",
    icon=":material/local_shipping:",
    help="Veículos cujo motorista está com status Ativo (PostgreSQL).",
    border=True,
)
kpi_temperatura.metric(
    "Temperatura média atual",
    f"{numero_br(temperatura_media)} °C" if temperatura_media is not None else "Sem dados",
    delta=f"última leitura de {indicadores['veiculos_com_telemetria']} veículos",
    delta_color="off",
    delta_arrow="off",
    icon=":material/thermostat:",
    help=(
        "Média da ÚLTIMA temperatura de cada veículo (MongoDB), não de todo o histórico. "
        "Junta cargas congeladas, refrigeradas e secas: a temperatura de cada uma está na tabela abaixo."
    ),
    border=True,
)
kpi_alertas.metric(
    "Alertas de velocidade",
    indicadores["alertas_velocidade"],
    delta=alertas_texto or f"nenhum veículo > {LIMITE_VELOCIDADE} km/h",
    delta_color="red" if alertas_texto else "green",
    delta_arrow="off",
    icon=":material/speed:",
    help=f"Veículos cuja última leitura está com velocidade > {LIMITE_VELOCIDADE} km/h (MongoDB).",
    border=True,
)
kpi_parados.metric(
    "Veículos parados",
    indicadores["veiculos_parados"],
    delta=", ".join(placas_paradas) or "nenhum veículo",
    delta_color="off",
    delta_arrow="off",
    icon=":material/pause_circle:",
    help="Veículos com velocidade 0 na última leitura.",
    border=True,
)

sem_telemetria = visao.loc[visao["timestamp"].isna(), "placa"].tolist()
if sem_telemetria:
    st.info(
        "Sem telemetria no MongoDB (fora da média, dos alertas, dos parados e do gráfico de velocidade): "
        + ", ".join(sem_telemetria),
        icon=":material/info:",
    )

# ============================================================
# SITUACÃO DE CADA VEÍCULO
# ============================================================

st.subheader("Situação de cada veículo")
st.caption("Cadastro (PostgreSQL) cruzado com a última leitura e o histórico de temperatura (MongoDB).")


def _destaque_situacao(valor: str) -> str:
    if valor.startswith("Acima"):
        return "color: #E63923; font-weight: 600"
    if valor == SITUACAO_PARADO:
        return "color: #5B6475"
    return ""


tabela_situacao = tabela_para_exibicao(
    situacao,
    ["placa", "motorista", "status_motorista", "situacao", "temperatura", "velocidade", "temperaturas", "timestamp"],
    rotulos={
        "status_motorista": "Status do motorista",
        "situacao": "Situação",
        "temperatura": "Temperatura",
        "temperaturas": "Temperatura nas leituras",
    },
).map(_destaque_situacao, subset=["Situação"])

st.dataframe(
    tabela_situacao,
    hide_index=True,
    width="stretch",
    placeholder=SEM_LEITURA,
    column_config={
        **CONFIG_COLUNAS,
        "Status do motorista": st.column_config.Column(help="PostgreSQL · status do motorista"),
        "Situação": st.column_config.Column(
            help=f"Pela última velocidade: em movimento, parado (0 km/h) ou acima de {LIMITE_VELOCIDADE} km/h."
        ),
        "Temperatura nas leituras": st.column_config.LineChartColumn(
            help="MongoDB · temperatura de cada leitura, da mais antiga à mais recente",
            width="medium",
        ),
    },
)

# ============================================================
# ESTADO ATUAL: VELOCIDADE E STATUS DOS MOTORISTAS
# ============================================================

coluna_velocidade, coluna_status = st.columns(2, gap="large", border=True)

with coluna_velocidade:
    st.subheader("Velocidade atual")
    st.caption(f"Barra vermelha: acima do limite de {LIMITE_VELOCIDADE} km/h (linha tracejada).")
    if visao["velocidade"].notna().any():
        st.plotly_chart(grafico_velocidade_atual(visao, LIMITE_VELOCIDADE), width="stretch")
    else:
        st.info("Sem leituras de velocidade.")

with coluna_status:
    st.subheader("Motoristas por status")
    st.caption("Todos os motoristas cadastrados no PostgreSQL.")
    if status.empty:
        st.info("Nenhum motorista cadastrado.")
    else:
        st.plotly_chart(grafico_status_motoristas(status), width="stretch")

# ============================================================
# HISTÓRICO DE TEMPERATURA
# ============================================================

st.subheader("Histórico de temperatura da carga")
st.caption(
    "Cada linha é um veículo e cada ponto, uma leitura do sensor. Veículos com cargas diferentes "
    "ficam em faixas diferentes de temperatura (uma carga congelada, por exemplo, fica abaixo de 0 °C)."
)

if historico.empty:
    st.info("Ainda não há leituras de telemetria no MongoDB.")
else:
    placas = sorted(historico["placa"].unique())
    escolhidas = st.multiselect(
        "Veículos no gráfico",
        placas,
        default=placas,
        placeholder="Escolha uma ou mais placas",
    )
    selecao = historico[historico["placa"].isin(escolhidas)].copy()

    if selecao.empty:
        st.info("Escolha ao menos um veículo para ver o histórico.")
    else:
        selecao["timestamp"] = horario_local(selecao["timestamp"])
        st.plotly_chart(grafico_historico_temperatura(selecao), width="stretch")
        st.caption(f"{len(selecao)} leituras · horário de Brasília.")
