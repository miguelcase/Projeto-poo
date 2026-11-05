"""Cesta Viva - controle de doações e estoque para bancos de alimentos comunitários.

Grupo Trio Ternário: Miguel Pires, Arthur Sacomorri e João Zamora.
Como executar: python main.py
"""
import os

from relatorio import Relatorio
from sistema import Sistema


def main() -> None:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))  # dados/, entrada/ e saida/ ficam ao lado do main.py
    sistema = Sistema()                # objeto 1: carrega dados/cesta_viva.json (ou cria a cesta padrão)
    relatorio = Relatorio(sistema)     # objeto 2: relatórios e gráficos lendo os dados do sistema
    sistema.executar(relatorio)


if __name__ == "__main__":
    main()
