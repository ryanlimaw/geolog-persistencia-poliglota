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
    conexao.autocommit = True
    return conexao

@st.cache_resource
def garantir_indices_telemetria():
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

    if conexao.closed:
        descartar_conexao_postgres(conexao)
        conexao = conectar_postgres()

    return conexao

def descartar_conexao_postgres(conexao=None):
    if conexao is not None and not conexao.closed:
        try:
            conexao.close()
        except pg.Error:
            pass
    conectar_postgres.clear()
