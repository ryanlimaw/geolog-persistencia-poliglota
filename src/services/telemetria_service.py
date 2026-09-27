from datetime import datetime, timedelta, timezone
from random import uniform
from typing import Any, Iterable, Optional

from db.clients import obter_banco_mongodb

# Acima deste valor (km/h) a leitura é um alerta de velocidade.
LIMITE_VELOCIDADE = 80

# ============================================================
# UTILITÁRIOS
# ============================================================

def _filtro_veiculos(veiculo_ids: Optional[Iterable[int]]) -> list[dict]:
    if veiculo_ids is None:
        return []
    return [{"$match": {"veiculo_id": {"$in": [int(v) for v in veiculo_ids]}}}]

def _etapas_ultima_leitura() -> list[dict]:
    """
    Uma leitura por veículo: a mais recente.

    Ordena por veículo e timestamp decrescente (usa o índice
    veiculo_id + timestamp) e fica com o primeiro documento de cada grupo.
    """
    return [
        {"$sort": {"veiculo_id": 1, "timestamp": -1}},
        {
            "$group": {
                "_id": "$veiculo_id",
                "telemetria_id": {"$first": "$_id"},
                "location": {"$first": "$location"},
                "temperatura": {"$first": "$temperatura"},
                "velocidade": {"$first": "$velocidade"},
                "timestamp": {"$first": "$timestamp"},
            }
        },
    ]

def pipeline_ultima_telemetria(veiculo_ids: Optional[Iterable[int]] = None) -> list[dict]:
    return [
        *_filtro_veiculos(veiculo_ids),
        *_etapas_ultima_leitura(),
        {
            "$project": {
                "_id": 0,
                "veiculo_id": "$_id",
                "telemetria_id": 1,
                "location": 1,
                "temperatura": 1,
                "velocidade": 1,
                "timestamp": 1,
            }
        },
        {"$sort": {"veiculo_id": 1}},
    ]

def pipeline_historico_temperatura(veiculo_ids: Optional[Iterable[int]] = None) -> list[dict]:
    return [
        *_filtro_veiculos(veiculo_ids),
        {"$project": {"_id": 0, "veiculo_id": 1, "timestamp": 1, "temperatura": 1}},
        {"$sort": {"timestamp": 1, "veiculo_id": 1}},
    ]

def pipeline_metricas_atuais(limite_velocidade: float = LIMITE_VELOCIDADE) -> list[dict]:
    """
    Métricas do ESTADO ATUAL da frota: só a última leitura de cada veículo
    entra na conta (a média de todo o histórico não é a temperatura atual).
    """
    return [
        *_etapas_ultima_leitura(),
        {
            "$group": {
                "_id": None,
                "veiculos_com_telemetria": {"$sum": 1},
                "temperatura_media": {"$avg": "$temperatura"},
                "alertas_velocidade": {
                    "$sum": {"$cond": [{"$gt": ["$velocidade", limite_velocidade]}, 1, 0]}
                },
                "veiculos_parados": {
                    "$sum": {"$cond": [{"$eq": ["$velocidade", 0]}, 1, 0]}
                },
                "ultimas": {"$push": {"veiculo_id": "$_id", "velocidade": "$velocidade"}},
            }
        },
        {
            "$project": {
                "_id": 0,
                "veiculos_com_telemetria": 1,
                "temperatura_media": 1,
                "alertas_velocidade": 1,
                "veiculos_parados": 1,
                "veiculos_em_alerta": {
                    "$map": {
                        "input": {
                            "$filter": {
                                "input": "$ultimas",
                                "cond": {"$gt": ["$$this.velocidade", limite_velocidade]},
                            }
                        },
                        "in": "$$this.veiculo_id",
                    }
                },
            }
        },
    ]

METRICAS_VAZIAS = {
    "veiculos_com_telemetria": 0,
    "temperatura_media": None,
    "alertas_velocidade": 0,
    "veiculos_parados": 0,
    "veiculos_em_alerta": [],
}

# ============================================================
# SERVIÇO
# ============================================================

class TelemetriaService:
    @property
    def mongo(self):
        return obter_banco_mongodb()

    @property
    def colecao(self):
        return self.mongo["telemetria"]

    def buscar_todos(self):
        return list(self.colecao.find())

    def simular_movimentacao(self, variacao_graus: float = 0.001) -> int:
        """Grava uma nova posição levemente deslocada para cada veículo atual."""
        ultimas = self.buscar_ultima_telemetria()
        agora = datetime.now(timezone.utc)
        leituras = []

        for indice, leitura in enumerate(ultimas):
            coordenadas = (leitura.get("location") or {}).get("coordinates") or []
            if len(coordenadas) != 2:
                continue

            longitude, latitude = coordenadas
            leituras.append(
                {
                    "veiculo_id": leitura["veiculo_id"],
                    "location": {
                        "type": "Point",
                        "coordinates": [
                            round(longitude + uniform(-variacao_graus, variacao_graus), 6),
                            round(latitude + uniform(-variacao_graus, variacao_graus), 6),
                        ],
                    },
                    "temperatura": round(leitura["temperatura"] + uniform(-0.2, 0.2), 1),
                    "velocidade": max(0, round(leitura["velocidade"] + uniform(-5, 5), 1)),
                    "timestamp": agora + timedelta(milliseconds=indice),
                }
            )

        if leituras:
            self.colecao.insert_many(leituras)

        return len(leituras)

    def _ids_ultimas_leituras(self) -> list:
        return [t["telemetria_id"] for t in self.colecao.aggregate(pipeline_ultima_telemetria())]

    def buscar_veiculos_e_distancia(self, latitude, longitude, raio) -> list[dict[str, Any]]:
        pipeline = [
            {
                "$geoNear": {
                    "near": {
                        "type": "Point",
                        "coordinates": [longitude, latitude],
                    },
                    "distanceField": "distancia_metros",
                    "maxDistance": raio * 1000,
                    "spherical": True,
                    "query": {"_id": {"$in": self._ids_ultimas_leituras()}},
                }
            }
        ]

        return list(self.colecao.aggregate(pipeline))

    def buscar_veiculos_proximos(self, latitude, longitude, raio) -> list[dict[str, Any]]:
        filtro = {
            "_id": {"$in": self._ids_ultimas_leituras()},
            "location": {
                "$geoWithin": {
                    "$centerSphere": [[longitude, latitude], raio / 6378.1]
                }
            },
        }

        return list(self.colecao.find(filtro))

    def buscar_ultima_telemetria(self, veiculo_ids: Optional[Iterable[int]] = None) -> list[dict[str, Any]]:
        return list(self.colecao.aggregate(pipeline_ultima_telemetria(veiculo_ids)))

    def buscar_historico_temperatura(self, veiculo_ids: Optional[Iterable[int]] = None) -> list[dict[str, Any]]:
        return list(self.colecao.aggregate(pipeline_historico_temperatura(veiculo_ids)))

    def buscar_metricas_atuais(self, limite_velocidade: float = LIMITE_VELOCIDADE) -> dict[str, Any]:
        resultado = list(self.colecao.aggregate(pipeline_metricas_atuais(limite_velocidade)))
        return resultado[0] if resultado else {**METRICAS_VAZIAS, "veiculos_em_alerta": []}
