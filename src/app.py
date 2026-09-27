from pathlib import Path

import streamlit as st

# Caminhos a partir deste arquivo: o app funciona rodando de qualquer pasta.
PASTA = Path(__file__).parent

# Layout largo: a visão integrada tem nove colunas e o dashboard, quatro KPIs lado a lado.
st.set_page_config(page_title="GeoLog · LogiTech Express", layout="wide")

# Com o layout largo, o logo fica na coluna do meio de três iguais (o mesmo
# tamanho que tinha no layout centralizado).
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    pass

with col2:
    st.image(PASTA / 'public' / 'logo-logitech-express.png')

with col3:
    pass

pages = [
    # A primeira página é a inicial e abre em "/" (url_path não vale para ela).
    st.Page(
        PASTA / "pages/home/index.py",
        title="Geolog",
        default=True,
    ),
    st.Page(
        PASTA / "pages/visao_geral/index.py",
        title="Visão Geral",
        url_path="visao-geral",
    ),
    st.Page(
        PASTA / "pages/dashboard/index.py",
        title="Dashboard da Frota",
        url_path="dashboard",
    ),
]

pg = st.navigation(pages, position="top")
pg.run()
