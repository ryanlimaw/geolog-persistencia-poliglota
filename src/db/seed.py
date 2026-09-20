import os
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
import psycopg2
from pymongo import MongoClient

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

TELEMETRIA_SEED = [
    {
        "veiculo_id": 101,

        "location": {
            "type": "Point",
            "coordinates": [-34.873, -7.115]
        },

        "temperatura": 4.2,
        "velocidade": 65,

        "timestamp": datetime.fromisoformat(
            "2026-09-11T10:00:00+00:00"
        )
    },

    {
        "veiculo_id": 102,

        "location": {
            "type": "Point",
            "coordinates": [-34.832, -7.121]
        },

        "temperatura": -18.5,
        "velocidade": 85,

        "timestamp": datetime.fromisoformat(
            "2026-09-11T10:05:00+00:00"
        )
    },

    {
        "veiculo_id": 103,

        "location": {
            "type": "Point",
            "coordinates": [-34.950, -7.150]
        },

        "temperatura": 22.0,
        "velocidade": 0,

        "timestamp": datetime.fromisoformat(
            "2026-09-11T09:45:00+00:00"
        )
    }
]


def criar_mongodb():
    print("Conectando ao MongoDB...")

    cliente = MongoClient(MONGO_URI)

    banco = cliente[MONGO_DB]

    colecao = banco["telemetria"]

    print("Limpando dados anteriores...")

    colecao.delete_many({})

    print("Inserindo telemetria...")

    if TELEMETRIA_SEED:
        colecao.insert_many(TELEMETRIA_SEED)

    print("Criando índice geoespacial...")

    colecao.create_index({
        "location": "2dsphere"
    })

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