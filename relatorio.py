"""Relatorio: relatórios em texto/CSV e gráficos em Matplotlib (responsável: João Zamora)."""
from __future__ import annotations

import csv
import os
from datetime import date
from typing import TYPE_CHECKING

try:
    import matplotlib
    matplotlib.use("Agg")            # só grava PNG, não abre janela
    import matplotlib.pyplot as plt
except ImportError:                  # o resto do sistema funciona sem os gráficos
    plt = None

from movimentacoes import Doacao

if TYPE_CHECKING:
    from sistema import Sistema

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
VERDE, LARANJA, AZUL = "#1F6F50", "#E08A2E", "#3D5A80"


class Relatorio:
    """Só consulta: lê os dados pelo Sistema e grava CSV e PNG na pasta de saída."""

    def __init__(self, sistema: Sistema, pasta_saida: str = "saida"):
        self.__sistema = sistema         # associação Relatorio -> Sistema
        self._pasta_saida = pasta_saida
        os.makedirs(pasta_saida, exist_ok=True)

    # ---------- relatórios (cada um devolve as linhas da tabela; a 1ª é o cabeçalho) ----------
    def estoque_atual(self) -> list[list]:
        estoque = self.__sistema.get_estoque()
        linhas = [["Produto", "Categoria", "Unid.", "Saldo", "Vence primeiro"]]
        for p in sorted(self.__sistema.get_produtos(), key=lambda p: (p.categoria, p.nome)):
            proxima = estoque.proximo_vencimento(p)
            linhas.append([p.nome, p.categoria, p.unidade, f"{estoque.saldo(p):g}",
                           proxima.strftime("%d/%m/%Y") if proxima else "-"])
        return linhas

    def doacoes_por_periodo(self, inicio: date, fim: date) -> list[list]:
        if inicio > fim:
            raise ValueError("A data de início é depois da data de fim.")
        linhas = [["Nº", "Data", "Doador", "Itens"]]
        total = 0.0
        for d in self.__doacoes():
            if inicio <= d.data <= fim:
                linhas.append([d.get_id(), d.data.strftime("%d/%m/%Y"), d.doador.nome, f"{d.total_itens():g}"])
                total += d.total_itens()
        linhas.append(["", "", "TOTAL", f"{total:g}"])
        return linhas

    def doacoes_por_doador(self) -> list[list]:
        linhas = [["Doador", "Tipo", "Doações", "Itens doados"]]
        for d in sorted(self.__sistema.get_doadores(), key=lambda d: d.total_doado(), reverse=True):
            linhas.append([d.nome, d.tipo or "-", len(d.get_doacoes()), f"{d.total_doado():g}"])
        return linhas

    def entregas_por_familia(self) -> list[list]:
        linhas = [["Família", "Pessoas", "Cestas", "Última entrega"]]
        for f in self.__sistema.get_familias():
            ultima = f.ultima_entrega()
            linhas.append([f.nome, f.num_pessoas, len(f.historico()),
                           ultima.strftime("%d/%m/%Y") if ultima else "nunca"])
        return linhas

    def formatar(self, linhas: list[list]) -> str:
        """Monta a tabela em texto com as colunas alinhadas."""
        larguras = [max(len(str(l[i])) for l in linhas) for i in range(len(linhas[0]))]
        return "\n".join("  ".join(str(c).ljust(w) for c, w in zip(l, larguras)).rstrip() for l in linhas)

    def exportar_csv(self, linhas: list[list], nome: str) -> str:
        caminho = os.path.join(self._pasta_saida, f"{nome}.csv")
        # utf-8-sig: o Excel abre com acentos certos; ';' é o separador que o Excel em português espera
        with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f, delimiter=";").writerows(linhas)
        return caminho

    # ---------- gráficos ----------
    def grafico_estoque_categoria(self) -> str:
        dados = dict(sorted(self.__sistema.get_estoque().saldo_por_categoria().items(), key=lambda kv: -kv[1]))
        fig, ax = self.__nova_figura("Estoque por categoria (itens válidos)")
        barras = ax.bar(list(dados), list(dados.values()), color=VERDE)
        ax.bar_label(barras, fmt="%g", fontsize=9)
        ax.tick_params(axis="x", rotation=30)
        return self.__salvar_png(fig, "estoque_categoria", dados)

    def grafico_doacoes_mes(self) -> str:
        por_mes: dict[tuple[int, int], float] = {}
        for d in self.__doacoes():
            chave = (d.data.year, d.data.month)
            por_mes[chave] = por_mes.get(chave, 0) + d.total_itens()
        chaves = sorted(por_mes)
        rotulos = [f"{MESES[m - 1]}/{a % 100:02d}" for a, m in chaves]
        valores = [por_mes[c] for c in chaves]
        fig, ax = self.__nova_figura("Doações por mês (itens)")
        ax.plot(rotulos, valores, marker="o", color=AZUL, linewidth=2)
        ax.margins(y=0.15)
        for x, y in zip(rotulos, valores):
            ax.annotate(f"{y:g}", (x, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=9)
        return self.__salvar_png(fig, "doacoes_mes", por_mes)

    def grafico_maiores_doadores(self, quantos: int = 5) -> str:
        doadores = sorted(self.__sistema.get_doadores(), key=lambda d: d.total_doado(), reverse=True)
        doadores = [d for d in doadores if d.total_doado() > 0][:quantos][::-1]   # maior fica em cima
        fig, ax = self.__nova_figura(f"Maiores doadores (top {quantos}, itens)")
        barras = ax.barh([d.nome for d in doadores], [d.total_doado() for d in doadores], color=LARANJA)
        ax.bar_label(barras, fmt="%g", fontsize=9, padding=3)
        return self.__salvar_png(fig, "maiores_doadores", doadores)

    # ---------- apoio interno ----------
    def __doacoes(self) -> list[Doacao]:
        return [m for m in self.__sistema.get_historico() if isinstance(m, Doacao)]

    def __nova_figura(self, titulo: str):
        if plt is None:
            raise RuntimeError("Matplotlib não está instalado. Rode: pip install matplotlib")
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.set_title(titulo, loc="left", fontweight="bold")
        ax.spines[["top", "right"]].set_visible(False)
        return fig, ax

    def __salvar_png(self, figura, nome: str, dados) -> str:
        if not dados:
            plt.close(figura)
            raise ValueError("Ainda não há dados para este gráfico.")
        caminho = os.path.join(self._pasta_saida, f"{nome}.png")
        figura.tight_layout()
        figura.savefig(caminho, dpi=150)
        plt.close(figura)
        return caminho

