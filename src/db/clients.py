import streamlit as st
from pymongo import MongoClient
import psycopg2 as pg 

@st.cache_resource
def conectar_mongodb():
    return MongoClient(
        st.secrets["mongodb"]["uri"],
        serverSelectionTimeoutMS=3000,
    )

@st.cache_resource
def conectar_postgres():
    return pg.connect(
        host=st.secrets["postgres"]["host"],
        port=st.secrets["postgres"]["port"],
        database=st.secrets["postgres"]["database"],
        user=st.secrets["postgres"]["user"],
        password=st.secrets["postgres"]["password"]
    )

def obter_banco_mongodb():
    cliente = conectar_mongodb()

    return cliente[
        st.secrets["mongodb"]["database"]
    ]

def obter_banco_postgres():
    conexao = conectar_postgres()

    return conexao