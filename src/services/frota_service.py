"""
Integração dos dois bancos (JOIN POLIGLOTA EM MEMÓRIA).

    PostgreSQL (VeiculoService)  → cadastro: veículo, placa, modelo, motorista, status
    MongoDB (TelemetriaService)  → última leitura: temperatura, velocidade, GeoJSON, horário
                   ↓
    FrotaService: junta os dois pelo veiculo_id, com pandas, em memória.

O resultado não é gravado em banco nenhum: cada banco continua dono dos
próprios dados, e a visão integrada é montada a cada consulta.
"""

from typing import Iterable, Optional

import pandas as pd

from services.telemetria_service import LIMITE_VELOCIDADE, TelemetriaService
from services.veiculos_service import VeiculoService

STATUS_ATIVO = "Ativo"

COLUNAS_FROTA = ["veiculo_id", "placa", "modelo", "motorista_id", "motorista", "status_motorista"]
COLUNAS_TELEMETRIA = ["veiculo_id", "temperatura", "velocidade", "latitude", "longitude", "timestamp"]
# Tipos fixos: com a telemetria vazia (ou um veículo sem leitura) o pandas
# deixaria as colunas numéricas como "object", e média, gráfico e formatação quebram.
TIPOS_TELEMETRIA = {
    "veiculo_id": "Int64",
    "temperatura": "float64",
    "velocidade": "float64",
    "latitude": "float64",
    "longitude": "float64",
}

COLUNAS_VISAO = [
    "veiculo_id",
    "placa",
    "modelo",
    "motorista",
    "status_motorista",
    "temperatura",
    "velocidade",
    "latitude",
    "longitude",
    "timestamp",
]


# ============================================================
# FUNÇÕES PURAS (testáveis sem banco)
# ============================================================

def coordenadas_do_geojson(location: Optional[dict]) -> tuple[Optional[float], Optional[float]]:
    """GeoJSON Point guarda [longitude, latitude]; devolve (latitude, longitude)."""
    coordenadas = (location or {}).get("coordinates") or []
    if len(coordenadas) != 2:
        return None, None
    longitude, latitude = coordenadas
    return latitude, longitude


def telemetria_em_tabela(telemetrias: Iterable[dict]) -> pd.DataFrame:
    linhas = []
    for leitura in telemetrias:
        latitude, longitude = coordenadas_do_geojson(leitura.get("location"))
        linhas.append(
            {
                "veiculo_id": leitura.get("veiculo_id"),
                "temperatura": leitura.get("temperatura"),
                "velocidade": leitura.get("velocidade"),
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": leitura.get("timestamp"),
            }
        )
    tabela = pd.DataFrame(linhas, columns=COLUNAS_TELEMETRIA).astype(TIPOS_TELEMETRIA)
    tabela["timestamp"] = pd.to_datetime(tabela["timestamp"], utc=True)
    return tabela


def montar_visao_integrada(frota: Iterable[dict], ultimas_telemetrias: Iterable[dict]) -> pd.DataFrame:
    """
    LEFT JOIN partindo da frota do PostgreSQL: um veículo cadastrado continua
    na tabela mesmo sem telemetria (as colunas do MongoDB ficam vazias).
    `validate` garante no máximo uma leitura por veículo (o estado atual).
    """
    tabela_frota = pd.DataFrame(list(frota), columns=COLUNAS_FROTA).astype({"veiculo_id": "Int64"})
    tabela_telemetria = telemetria_em_tabela(ultimas_telemetrias)

    visao = tabela_frota.merge(
        tabela_telemetria,
        on="veiculo_id",
        how="left",
        validate="one_to_one",
    )
    return visao[COLUNAS_VISAO]


def calcular_frota_ativa(frota: Iterable[dict]) -> int:
    """Frota ativa = veículos cujo motorista está com status "Ativo"."""
    return sum(1 for veiculo in frota if veiculo.get("status_motorista") == STATUS_ATIVO)


def historico_com_placa(historico: Iterable[dict], frota: Iterable[dict]) -> pd.DataFrame:
    """Histórico de temperatura com a placa do veículo (vinda do PostgreSQL)."""
    placas = {veiculo["veiculo_id"]: veiculo["placa"] for veiculo in frota}
    tabela = pd.DataFrame(list(historico), columns=["veiculo_id", "timestamp", "temperatura"])
    tabela = tabela.astype({"veiculo_id": "Int64", "temperatura": "float64"})
    tabela["placa"] = tabela["veiculo_id"].map(placas).fillna("Sem cadastro")
    tabela["timestamp"] = pd.to_datetime(tabela["timestamp"], utc=True)
    return tabela.sort_values(["timestamp", "veiculo_id"]).reset_index(drop=True)


SITUACAO_SEM_TELEMETRIA = "Sem telemetria"
SITUACAO_ALERTA = "Acima de {limite:.0f} km/h"
SITUACAO_PARADO = "Parado"
SITUACAO_MOVIMENTO = "Em movimento"


def classificar_situacao(velocidade: Optional[float], limite_velocidade: float = LIMITE_VELOCIDADE) -> str:
    """Situação do veículo pela velocidade da última leitura."""
    if velocidade is None or pd.isna(velocidade):
        return SITUACAO_SEM_TELEMETRIA
    if velocidade > limite_velocidade:
        return SITUACAO_ALERTA.format(limite=limite_velocidade)
    if velocidade == 0:
        return SITUACAO_PARADO
    return SITUACAO_MOVIMENTO


def situacao_por_veiculo(
    visao: pd.DataFrame, historico: pd.DataFrame, limite_velocidade: float = LIMITE_VELOCIDADE
) -> pd.DataFrame:
    """
    Uma linha por veículo para o dashboard: a visão integrada mais a
    situação atual e a sequência de temperaturas (para o mini-gráfico).
    Usa só os dados já carregados; não consulta banco.
    """
    temperaturas = (
        historico.sort_values("timestamp").groupby("veiculo_id")["temperatura"].apply(list)
        if not historico.empty
        else pd.Series(dtype="object")
    )
    tabela = visao.copy()
    tabela["situacao"] = [classificar_situacao(v, limite_velocidade) for v in tabela["velocidade"]]
    tabela["temperaturas"] = [temperaturas.get(v, []) for v in tabela["veiculo_id"]]
    return tabela


# ============================================================
# SERVIÇO
# ============================================================

class FrotaService:
    def __init__(self):
        self.veiculos = VeiculoService()
        self.telemetria = TelemetriaService()

    def listar_frota(self) -> list[dict]:
        return self.veiculos.listar_frota()                    

    def visao_integrada(self, frota: Optional[list[dict]] = None) -> pd.DataFrame:
        frota = self.listar_frota() if frota is None else frota
        ultimas = self.telemetria.buscar_ultima_telemetria()    # 1 pipeline no MongoDB
        return montar_visao_integrada(frota, ultimas)

    def historico_temperatura(
        self, veiculo_ids: Optional[Iterable[int]] = None, frota: Optional[list[dict]] = None
    ) -> pd.DataFrame:
        frota = self.listar_frota() if frota is None else frota
        historico = self.telemetria.buscar_historico_temperatura(veiculo_ids)
        return historico_com_placa(historico, frota)

    def indicadores(
        self, limite_velocidade: float = LIMITE_VELOCIDADE, frota: Optional[list[dict]] = None
    ) -> dict:
        frota = self.listar_frota() if frota is None else frota
        metricas = self.telemetria.buscar_metricas_atuais(limite_velocidade)
        placas = {veiculo["veiculo_id"]: veiculo["placa"] for veiculo in frota}

        return {
            "frota_total": len(frota),
            "frota_ativa": calcular_frota_ativa(frota),
            "temperatura_media": metricas["temperatura_media"],
            "alertas_velocidade": metricas["alertas_velocidade"],
            "placas_em_alerta": sorted(placas.get(v, f"Veículo {v}") for v in metricas["veiculos_em_alerta"]),
            "veiculos_parados": metricas["veiculos_parados"],
            "veiculos_com_telemetria": metricas["veiculos_com_telemetria"],
        }

    def motoristas_por_status(self) -> pd.DataFrame:
        return pd.DataFrame(self.veiculos.contar_motoristas_por_status(), columns=["status", "quantidade"])
