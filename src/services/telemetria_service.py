from typing import Any
from src.db.clients import obter_banco_mongodb

class TelemetriaService:
    def __init__(self):
        self.mongo = obter_banco_mongodb()

    def buscar_todos(self):
        return list(self.mongo["telemetria"].find())

    def buscar_veiculos_por_raio(self, latitude, longitude, raio) -> list[dict[str, Any]]:
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
                }
            }
        ]

        return list(self.mongo["telemetria"].aggregate(pipeline))

    def buscar_veiculos_proximos(self, latitude, longitude, raio) -> list[dict[str, Any]]:
        pipeline = {
            "location": {
                "$geoWithin": {
                    "$centerSphere": [[longitude, latitude], raio / 6378.1]
                }
            }
        }

        return list(self.mongo["telemetria"].find(pipeline))