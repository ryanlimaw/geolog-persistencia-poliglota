import streamlit as st
from pymongo import ASCENDING, DESCENDING, GEOSPHERE, MongoClient
import psycopg2 as pg

@st.cache_resource
def conectar_mongodb():
    return MongoClient(
        st.secrets["mongodb"]["uri"],
        serverSelectionTimeoutMS=3000,
    )

@st.cache_resource
def conectar_postgres():
    conexao = pg.connect(
        host=st.secrets["postgres"]["host"],
        port=st.secrets["postgres"]["port"],
        database=st.secrets["postgres"]["database"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"],
        connect_timeout=3,
    )
    # A aplicação só LÊ do PostgreSQL. Em autocommit cada consulta é a sua
    # própria transação: um SELECT com erro não deixa a conexão cacheada
    # presa em "current transaction is aborted".
    conexao.autocommit = True
    return conexao

@st.cache_resource
def garantir_indices_telemetria():
    """
    Cria os índices da coleção de telemetria na inicialização da aplicação,
    uma vez por processo (`create_index` não faz nada se o índice já existe):

    - location (2dsphere): exigido pelas consultas geoespaciais ($geoNear, $geoWithin);
    - veiculo_id + timestamp (desc): atende a última leitura por veículo e o histórico.
    """
    telemetria = conectar_mongodb()[st.secrets["mongodb"]["database"]]["telemetria"]
    telemetria.create_index([("location", GEOSPHERE)])
    telemetria.create_index([("veiculo_id", ASCENDING), ("timestamp", DESCENDING)])
    return True

def obter_banco_mongodb():
    cliente = conectar_mongodb()
    garantir_indices_telemetria()

    return cliente[
        st.secrets["mongodb"]["database"]
    ]

def obter_banco_postgres():
    conexao = conectar_postgres()

    # Se o servidor caiu desde a última consulta, abre uma conexão nova.
    if conexao.closed:
        descartar_conexao_postgres(conexao)
        conexao = conectar_postgres()

    return conexao

def descartar_conexao_postgres(conexao=None):
    """Fecha a conexão (se recebida) e a tira do cache: a próxima consulta reconecta."""
    if conexao is not None and not conexao.closed:
        try:
            conexao.close()
        except pg.Error:
            pass
    conectar_postgres.clear()
