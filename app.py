"""
Explorador interativo de vendas — 2024
======================================
Aplicativo web desenvolvido com Shiny para Python + Plotly.

Conjunto de dados: dados_vendas_2024.csv
    - Variáveis numéricas: vendas, quantidade, lucro
    - Variáveis categóricas: produto, categoria, regiao
    - Período: data (diária, janeiro a abril de 2024)

Como executar:
    .venv/bin/shiny run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget

# ---------------------------------------------------------------------------
# 1. Dados
# ---------------------------------------------------------------------------
ARQUIVO = Path(__file__).parent / "dados_vendas_2024.csv"
dados = pd.read_csv(ARQUIVO, parse_dates=["data"])

VARIAVEIS = {
    "vendas": "Vendas (R$)",
    "quantidade": "Quantidade",
    "lucro": "Lucro (R$)",
}
REGIOES = sorted(dados["regiao"].unique().tolist())
CATEGORIAS = sorted(dados["categoria"].unique().tolist())
DATA_MIN = dados["data"].min().date()
DATA_MAX = dados["data"].max().date()

ROTULOS = {
    **VARIAVEIS,
    "regiao": "Região",
    "produto": "Produto",
    "categoria": "Categoria",
    "data": "Data",
}

# ---------------------------------------------------------------------------
# 2. Interface (UI)
# ---------------------------------------------------------------------------
app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.h4("Painel de controle"),
        ui.input_select(
            "var_x",
            "Variável do eixo X / histograma:",
            choices=VARIAVEIS,
            selected="vendas",
        ),
        ui.input_select(
            "var_y",
            "Variável do eixo Y / boxplot:",
            choices=VARIAVEIS,
            selected="lucro",
        ),
        ui.input_date_range(
            "periodo",
            "Período:",
            start=DATA_MIN,
            end=DATA_MAX,
            min=DATA_MIN,
            max=DATA_MAX,
            language="pt-BR",
            separator=" a ",
        ),
        ui.input_checkbox_group(
            "regioes",
            "Regiões:",
            choices=REGIOES,
            selected=REGIOES,
        ),
        ui.input_checkbox_group(
            "categorias",
            "Categorias:",
            choices=CATEGORIAS,
            selected=CATEGORIAS,
        ),
        ui.input_checkbox("agrupar", "Agrupar por região (cores)", value=True),
        ui.input_checkbox("log_x", "Escala logarítmica no eixo X", value=False),
        ui.input_slider(
            "bins",
            "Número de classes do histograma:",
            min=5,
            max=60,
            value=25,
        ),
        width=320,
    ),
    ui.div(
        ui.h2("Explorador interativo de vendas — 2024"),
        ui.p(
            "Este aplicativo explora vendas diárias de alimentos, eletrônicos, livros "
            "e roupas, de janeiro a abril de 2024. Use o painel à esquerda para escolher "
            "as variáveis, filtrar por período, região e categoria e agrupar os dados. "
            "Os gráficos e a tabela de estatísticas descritivas se atualizam automaticamente."
        ),
        ui.output_text("resumo_filtro"),
    ),
    ui.layout_columns(
        ui.card(ui.card_header("Distribuição (histograma)"), output_widget("histograma")),
        ui.card(ui.card_header("Comparação entre grupos (boxplot)"), output_widget("boxplot")),
        col_widths=[6, 6],
    ),
    ui.card(ui.card_header("Relação entre variáveis (dispersão)"), output_widget("dispersao")),
    ui.card(
        ui.card_header("Estatísticas descritivas"),
        ui.output_table("tabela_estatisticas"),
    ),
    title="Shiny + Plotly",
    fillable=False,
)

# ---------------------------------------------------------------------------
# 3. Servidor (lógica reativa)
# ---------------------------------------------------------------------------
def server(input, output, session):

    @reactive.calc
    def dados_filtrados() -> pd.DataFrame:
        """Aplica os filtros de período, região e categoria."""
        inicio, fim = input.periodo()
        df = dados[
            dados["data"].between(pd.to_datetime(inicio), pd.to_datetime(fim))
            & dados["regiao"].isin(input.regioes())
            & dados["categoria"].isin(input.categorias())
        ]
        return df

    def cor():
        """Retorna a coluna de agrupamento (ou None) conforme o checkbox."""
        return "regiao" if input.agrupar() else None

    @render.text
    def resumo_filtro():
        df = dados_filtrados()
        inicio, fim = input.periodo()
        ini = pd.to_datetime(inicio).strftime("%d/%m/%Y")
        end = pd.to_datetime(fim).strftime("%d/%m/%Y")
        return (
            f"Observações selecionadas: {len(df)} | "
            f"Regiões: {df['regiao'].nunique()} | "
            f"Período: {ini}–{end}"
        )

    @render_widget
    def histograma():
        df = dados_filtrados()
        fig = px.histogram(
            df,
            x=input.var_x(),
            color=cor(),
            nbins=input.bins(),
            log_x=input.log_x(),
            barmode="overlay",
            opacity=0.75,
            labels=ROTULOS,
        )
        fig.update_layout(yaxis_title="Frequência", margin=dict(t=30))
        return fig

    @render_widget
    def boxplot():
        df = dados_filtrados()
        y = input.var_y()
        if input.agrupar():
            fig = px.box(
                df,
                x="regiao",
                y=y,
                color="regiao",
                points="outliers",
                labels=ROTULOS,
            )
            fig.update_layout(showlegend=False)
        else:
            fig = px.box(df, y=y, points="outliers", labels=ROTULOS)
        fig.update_layout(margin=dict(t=30))
        return fig

    @render_widget
    def dispersao():
        df = dados_filtrados()
        fig = px.scatter(
            df,
            x=input.var_x(),
            y=input.var_y(),
            color=cor(),
            size="quantidade",
            size_max=40,
            hover_name="produto",
            hover_data={"data": True, "categoria": True},
            log_x=input.log_x(),
            opacity=0.7,
            labels=ROTULOS,
        )
        fig.update_layout(margin=dict(t=30))
        return fig

    @render.table
    def tabela_estatisticas():
        df = dados_filtrados()
        if df.empty:
            return pd.DataFrame({"Aviso": ["Nenhum dado para os filtros selecionados."]})

        colunas = list(VARIAVEIS.keys())
        funcoes = ["count", "mean", "std", "min", "median", "max"]
        nomes = {
            "count": "n",
            "mean": "Média",
            "std": "Desvio-padrão",
            "min": "Mínimo",
            "median": "Mediana",
            "max": "Máximo",
        }

        if input.agrupar():
            tab = (
                df.groupby("regiao")[colunas]
                .agg(funcoes)
                .stack(level=0, future_stack=True)
                .reset_index()
                .rename(columns={"regiao": "Região", "level_1": "Variável"})
            )
        else:
            tab = (
                df[colunas]
                .agg(funcoes)
                .T.reset_index()
                .rename(columns={"index": "Variável"})
            )

        tab["Variável"] = tab["Variável"].map(VARIAVEIS)
        tab = tab.rename(columns=nomes)
        tab["n"] = tab["n"].astype(int)
        for c in ["Média", "Desvio-padrão", "Mínimo", "Mediana", "Máximo"]:
            tab[c] = tab[c].map(
                lambda v: f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        return tab


app = App(app_ui, server)
