"""
Peças comuns da Visão Geral e do Dashboard: carregamento dos dados (com
cache curto), mensagem de erro por banco e formatação para exibição.

As páginas não falam com banco nenhum: pedem os dados ao FrotaService.
"""

import pandas as pd
import psycopg2
import streamlit as st
from pymongo.errors import PyMongoError
from streamlit.errors import StreamlitSecretNotFoundError

from services.frota_service import FrotaService

# A telemetria muda: o cache vale poucos segundos, e o botão "Atualizar
# dados" força uma leitura nova na hora.
TTL_DADOS = 30

FUSO_LOCAL = "America/Recife"

ROTULOS = {
    "motorista": "Motorista",
    "placa": "Placa",
    "modelo": "Modelo",
    "status_motorista": "Status",
    "temperatura": "Última Temperatura",
    "velocidade": "Velocidade",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "timestamp": "Última Atualização",
}

# De qual banco vem cada coluna (aparece ao passar o cursor no nome).
CONFIG_COLUNAS = {
    "Motorista": st.column_config.Column(help="PostgreSQL · motoristas"),
    "Placa": st.column_config.Column(help="PostgreSQL · veiculos"),
    "Modelo": st.column_config.Column(help="PostgreSQL · veiculos"),
    "Status": st.column_config.Column(help="PostgreSQL · status do motorista"),
    "Última Temperatura": st.column_config.Column(help="MongoDB · última leitura"),
    "Temperatura": st.column_config.Column(help="MongoDB · última leitura"),
    "Velocidade": st.column_config.Column(help="MongoDB · última leitura"),
    "Latitude": st.column_config.Column(help="MongoDB · GeoJSON (coordinates[1])"),
    "Longitude": st.column_config.Column(help="MongoDB · GeoJSON (coordinates[0])"),
    "Última Atualização": st.column_config.Column(help="MongoDB · horário da última leitura (hora de Brasília)"),
}

# Texto das células sem leitura (veículo sem telemetria), no lugar de "None".
SEM_LEITURA = "—"

# Formato de exibição em pt-BR (vírgula decimal).
FORMATOS = {
    "Última Temperatura": "{:.1f} °C",
    "Temperatura": "{:.1f} °C",
    "Velocidade": "{:.0f} km/h",
    "Latitude": "{:.5f}",
    "Longitude": "{:.5f}",
    "Última Atualização": lambda horario: horario.strftime("%d/%m/%Y %H:%M"),
}


# ============================================================
# DADOS
# ============================================================

@st.cache_resource
def _frota_service() -> FrotaService:
    return FrotaService()


# A frota (PostgreSQL) é carregada uma vez e repassada aos três carregadores
# abaixo: antes cada um fazia a mesma consulta.
@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def carregar_frota() -> list[dict]:
    return _frota_service().listar_frota()


@st.cache_data(ttl=TTL_DADOS, show_spinner="Consultando PostgreSQL e MongoDB...")
def carregar_visao_integrada() -> pd.DataFrame:
    return _frota_service().visao_integrada(frota=carregar_frota())


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def carregar_indicadores() -> dict:
    return _frota_service().indicadores(frota=carregar_frota())


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def carregar_historico_temperatura() -> pd.DataFrame:
    return _frota_service().historico_temperatura(frota=carregar_frota())


@st.cache_data(ttl=TTL_DADOS, show_spinner=False)
def carregar_motoristas_por_status() -> pd.DataFrame:
    return _frota_service().motoristas_por_status()


def botao_atualizar():
    if st.button("Atualizar dados", icon=":material/refresh:", help=f"Os dados ficam em cache por {TTL_DADOS} s."):
        st.cache_data.clear()
        st.rerun()


# ============================================================
# ERROS
# ============================================================

def mostrar_falha(erro: Exception):
    """Mensagem clara de qual banco falhou, com o erro técnico num expander."""
    if isinstance(erro, PyMongoError):
        mensagem = (
            "Não foi possível consultar o **MongoDB** (telemetria). "
            "Confira se o banco está no ar (`docker compose up -d`) e a seção `[mongodb]` do `secrets.toml`."
        )
    elif isinstance(erro, psycopg2.Error):
        mensagem = (
            "Não foi possível consultar o **PostgreSQL** (veículos e motoristas). "
            "Confira se o banco está no ar (`docker compose up -d`) e a seção `[postgres]` do `secrets.toml`."
        )
    elif isinstance(erro, (StreamlitSecretNotFoundError, KeyError)):
        mensagem = (
            "Configuração de acesso aos bancos ausente ou incompleta. "
            "Copie `src/.streamlit/secrets-example.toml` para `src/.streamlit/secrets.toml` e preencha."
        )
    else:
        mensagem = "Erro inesperado ao carregar os dados da frota."

    st.error(mensagem, icon=":material/error:")
    with st.expander("Detalhes técnicos"):
        st.exception(erro)


# ============================================================
# EXIBIÇÃO
# ============================================================

def horario_local(serie: pd.Series) -> pd.Series:
    """Horários guardados em UTC, exibidos na hora de Brasília."""
    return pd.to_datetime(serie, utc=True).dt.tz_convert(FUSO_LOCAL)


def tabela_para_exibicao(visao: pd.DataFrame, colunas: list[str], rotulos: dict | None = None):
    """
    Só as colunas pedidas, com nomes amigáveis, horário local e números em
    pt-BR (sem ids internos). Devolve um Styler: os valores continuam
    numéricos (a ordenação da tabela funciona), só a exibição muda.
    """
    tabela = visao[colunas].copy()
    if "timestamp" in tabela:
        tabela["timestamp"] = horario_local(tabela["timestamp"])
    tabela = tabela.rename(columns={**ROTULOS, **(rotulos or {})})
    formatos = {coluna: formato for coluna, formato in FORMATOS.items() if coluna in tabela}
    return tabela.style.format(formatos, decimal=",", thousands=".", na_rep=SEM_LEITURA)


def numero_br(valor: float, casas: int = 1) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")
