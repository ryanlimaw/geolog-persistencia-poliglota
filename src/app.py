import streamlit as st

col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    pass

with col2:
    st.image('src/public/logo-logitech-express.png')

with col3:
    pass

pages = [
    st.Page(
        "pages/home/index.py",
        title="Geolog",
        url_path="home",
    ),
    st.Page(
        "pages/visao_geral/index.py",
        title="Visão Geral",
        url_path="visao-geral",
    ),
    st.Page(
        "pages/dashboard/index.py",
        title="Dashboard da Frota",
        url_path="dashboard",
    ),
]

pg = st.navigation(pages, position="top")
pg.run()



