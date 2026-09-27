import os
from dotenv import load_dotenv, find_dotenv
from datetime import datetime, timedelta
import psycopg2
from pymongo import ASCENDING, DESCENDING, GEOSPHERE, MongoClient

load_dotenv(find_dotenv())


# ============================================================
# CONFIGURAÇÕES
# ============================================================

POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")


# ============================================================
# SEED - POSTGRESQL
# ============================================================

MOTORISTAS = [
    (1, "Carlos Andrade", "123456789", "Ativo"),
    (2, "Mariana Silva", "987654321", "Ativo"),
    (3, "Roberto Souza", "456789123", "Em Descanso"),
]


VEICULOS = [
    (101, "ABC-1A23", "Volvo FH 540", 1),
    (102, "XYZ-9876", "Scania R450", 2),
    (103, "KGB-4567", "Mercedes Actros", 3),
]


def criar_postgresql():
    print("Conectando ao PostgreSQL...")

    conexao = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )

    cursor = conexao.cursor()

    print("Criando tabelas...")

    cursor.execute("""
        DROP TABLE IF EXISTS veiculos;
        DROP TABLE IF EXISTS motoristas;
    """)

    cursor.execute("""
        CREATE TABLE motoristas (
            id INTEGER PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            cnh VARCHAR(20) NOT NULL UNIQUE,
            status VARCHAR(30) NOT NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE veiculos (
            id INTEGER PRIMARY KEY,
            placa VARCHAR(8) NOT NULL UNIQUE,
            modelo VARCHAR(100) NOT NULL,
            motorista_id INTEGER NOT NULL,

            CONSTRAINT fk_veiculo_motorista
                FOREIGN KEY (motorista_id)
                REFERENCES motoristas(id)
        );
    """)

    print("Inserindo motoristas...")

    cursor.executemany("""
        INSERT INTO motoristas (
            id,
            nome,
            cnh,
            status
        )
        VALUES (%s, %s, %s, %s);
    """, MOTORISTAS)

    print("Inserindo veículos...")

    cursor.executemany("""
        INSERT INTO veiculos (
            id,
            placa,
            modelo,
            motorista_id
        )
        VALUES (%s, %s, %s, %s);
    """, VEICULOS)

    conexao.commit()

    cursor.close()
    conexao.close()

    print("PostgreSQL configurado com sucesso.")


# ============================================================
# SEED - MONGODB
# ============================================================

# Histórico de telemetria: 12 leituras por veículo, de 10 em 10 minutos.
# Determinístico (nada aleatório): rodar o seed de novo gera os mesmos dados.
#
# A ÚLTIMA leitura de cada veículo é a do seed sugerido no enunciado
# (mesmas coordenadas, temperatura, velocidade e horário), então o estado
# atual da frota continua o mesmo:
#   101: operação normal, carga refrigerada (~4 °C);
#   102: carga congelada (~-18 °C), várias leituras acima de 80 km/h;
#   103: carga seca (~22 °C), desacelera e termina parado (velocidade 0).
#
# As posições anteriores são calculadas para trás a partir da posição
# final: entre uma leitura e a seguinte o veículo anda uma distância
# proporcional à velocidade registrada na leitura de saída, sempre na mesma
# direção. Veículo parado não se move. A escala (GRAUS_POR_KMH) é de
# demonstração: mantém o percurso perto de João Pessoa, não é a distância
# real. GeoJSON Point: [longitude, latitude].

INTERVALO_LEITURAS = timedelta(minutes=10)

# Graus percorridos em 10 minutos por km/h de velocidade (escala da demonstração).
GRAUS_POR_KMH = 0.0001

PERCURSOS = [
    {
        "veiculo_id": 101,
        "posicao_final": [-34.873, -7.115],  # João Pessoa (Centro)
        "horario_final": "2026-09-11T10:00:00+00:00",
        "direcao": [0.9, 0.3],  # vem do oeste, levemente do sul
        "temperaturas": [3.8, 3.9, 4.0, 4.1, 4.3, 4.4, 4.2, 4.0, 3.9, 4.1, 4.3, 4.2],
        "velocidades": [45, 52, 58, 61, 63, 66, 70, 68, 64, 62, 60, 65],
    },
    {
        "veiculo_id": 102,
        "posicao_final": [-34.832, -7.121],  # Cabo Branco
        "horario_final": "2026-09-11T10:05:00+00:00",
        "direcao": [1.0, 0.0],  # vem do oeste, rumo à orla
        "temperaturas": [-19.2, -19.0, -18.8, -18.9, -18.6, -18.4, -18.7, -18.9, -18.6, -18.3, -18.4, -18.5],
        "velocidades": [60, 68, 74, 79, 82, 88, 84, 78, 76, 81, 83, 85],
    },
    {
        "veiculo_id": 103,
        "posicao_final": [-34.950, -7.150],  # Tibiri / BR-230
        "horario_final": "2026-09-11T09:45:00+00:00",
        "direcao": [0.8, -0.6],  # vem do sudoeste
        "temperaturas": [21.0, 21.2, 21.4, 21.5, 21.7, 21.8, 21.9, 22.1, 22.0, 22.1, 22.0, 22.0],
        "velocidades": [55, 58, 52, 47, 40, 32, 21, 12, 5, 0, 0, 0],
    },
]


def gerar_telemetria() -> list[dict]:
    leituras = []

    for percurso in PERCURSOS:
        velocidades = percurso["velocidades"]
        total = len(velocidades)
        longitude_final, latitude_final = percurso["posicao_final"]
        direcao_lon, direcao_lat = percurso["direcao"]
        horario_final = datetime.fromisoformat(percurso["horario_final"])

        for i in range(total):
            # Distância que ainda falta da leitura i até a final: soma das
            # velocidades de saída dos trechos i→i+1, ..., penúltima→última.
            falta = sum(velocidades[i:total - 1]) * GRAUS_POR_KMH

            leituras.append({
                "veiculo_id": percurso["veiculo_id"],

                "location": {
                    "type": "Point",
                    "coordinates": [
                        round(longitude_final - direcao_lon * falta, 6),
                        round(latitude_final - direcao_lat * falta, 6),
                    ]
                },

                "temperatura": percurso["temperaturas"][i],
                "velocidade": velocidades[i],

                "timestamp": horario_final - INTERVALO_LEITURAS * (total - 1 - i)
            })

    return leituras


TELEMETRIA_SEED = gerar_telemetria()


def criar_mongodb():
    print("Conectando ao MongoDB...")

    cliente = MongoClient(MONGO_URI)

    banco = cliente[MONGO_DB]

    colecao = banco["telemetria"]

    print("Limpando dados anteriores...")

    colecao.delete_many({})

    # Índices ANTES da carga: um GeoJSON inválido é recusado na inserção,
    # em vez de a carga passar e só a criação do índice falhar depois.
    # (A aplicação também garante os dois ao conectar: db/clients.py.)
    print("Criando índices (2dsphere e veiculo_id + timestamp)...")

    colecao.create_index([("location", GEOSPHERE)])
    colecao.create_index([("veiculo_id", ASCENDING), ("timestamp", DESCENDING)])

    print(f"Inserindo telemetria ({len(TELEMETRIA_SEED)} leituras)...")

    if TELEMETRIA_SEED:
        colecao.insert_many(TELEMETRIA_SEED)

    cliente.close()

    print("MongoDB configurado com sucesso.")


# ============================================================
# EXECUÇÃO
# ============================================================

def main():
    print("=" * 50)
    print("GERAÇÃO DAS SEEDS")
    print("=" * 50)

    criar_postgresql()

    print()

    criar_mongodb()

    print()
    print("=" * 50)
    print("SEEDS GERADAS COM SUCESSO!")
    print("=" * 50)


if __name__ == "__main__":
    main()