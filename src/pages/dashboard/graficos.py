import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# CONSTANTES DE EXIBIÇÃO
# ============================================================

# Cores oficiais do tema em src/.streamlit/config.toml.
AZUL_MARCA = st.get_option("theme.textColor")
VERMELHO_MARCA = st.get_option("theme.primaryColor")
# Texto do centro da rosca: a cor de texto do tema (a de fundo secundário é
# branca, e o total ficava invisível sobre o cartão).
CINZA_TEXTO = st.get_option("theme.textColor")
CORES_CATEGORIAS = st.get_option("theme.chartCategoricalColors")

MARGENS = dict(l=10, r=10, t=10, b=10)

# Os dois gráficos do "estado atual" ficam lado a lado com a mesma altura.
ALTURA_LADO_A_LADO = 340

# Números em pt-BR nos gráficos: vírgula decimal, ponto de milhar.
SEPARADORES = ",."


def grafico_historico_temperatura(historico: pd.DataFrame) -> go.Figure:
    """Linha da temperatura ao longo do tempo, uma cor por placa."""
    figura = px.line(
        historico,
        x="timestamp",
        y="temperatura",
        color="placa",
        markers=True,
        color_discrete_sequence=CORES_CATEGORIAS,
        category_orders={"placa": sorted(historico["placa"].unique())},
        labels={"timestamp": "Horário (Brasília)", "temperatura": "Temperatura da carga", "placa": "Placa"},
    )
    figura.update_traces(hovertemplate="%{fullData.name}: %{y:.1f} °C<extra></extra>")
    figura.update_layout(
        height=380,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
        margin=MARGENS,
        separators=SEPARADORES,
    )
    # Dia e hora: com leituras simuladas o histórico passa a cobrir mais de um dia.
    figura.update_xaxes(tickformat="%d/%m %H:%M")
    figura.update_yaxes(ticksuffix=" °C", zeroline=True, zerolinecolor="#D9D9D9")
    return figura

def grafico_velocidade_atual(visao: pd.DataFrame, limite: float) -> go.Figure:
    dados = visao.dropna(subset=["velocidade"]).sort_values("placa")
    em_alerta = dados["velocidade"] > limite

    figura = go.Figure(
        go.Bar(
            x=dados["placa"],
            y=dados["velocidade"],
            marker_color=[VERMELHO_MARCA if alerta else AZUL_MARCA for alerta in em_alerta],
            text=["Parado" if v == 0 else f"{v:.0f} km/h" for v in dados["velocidade"]],
            textposition="outside",
            customdata=dados["motorista"],
            hovertemplate="%{x} · %{customdata}<br>%{y:.0f} km/h<extra></extra>",
        )
    )
    figura.add_hline(
        y=limite,
        line_dash="dash",
        line_color=VERMELHO_MARCA,
        annotation_text=f"Limite: {limite:.0f} km/h",
        annotation_position="top left",
        annotation_font_color=VERMELHO_MARCA,
    )
    maior = max([limite, *dados["velocidade"].tolist()])
    figura.update_layout(
        height=ALTURA_LADO_A_LADO,
        yaxis=dict(title="", range=[0, maior * 1.25], ticksuffix=" km/h"),
        xaxis=dict(title=""),
        showlegend=False,
        margin=MARGENS,
        separators=SEPARADORES,
    )
    return figura

def grafico_status_motoristas(status: pd.DataFrame) -> go.Figure:
    figura = px.pie(
        status,
        names="status",
        values="quantidade",
        hole=0.6,
        color_discrete_sequence=CORES_CATEGORIAS,
    )
    figura.update_traces(
        textinfo="value",
        textfont_size=15,
        hovertemplate="%{label}: %{value} motorista(s) (%{percent})<extra></extra>",
        sort=False,
    )
    total = int(status["quantidade"].sum())
    figura.add_annotation(
        text=f"<b>{total}</b><br>motoristas",
        showarrow=False,
        font=dict(size=16, color=CINZA_TEXTO),
    )
    figura.update_layout(
        height=ALTURA_LADO_A_LADO,
        legend=dict(orientation="h", yanchor="top", y=-0.02, x=0.5, xanchor="center"),
        margin=MARGENS,
        separators=SEPARADORES,
    )
    return figura
