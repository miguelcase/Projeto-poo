"""Módulo Movimentações: Doacao e Entrega (responsável: Arthur Sacomorri)."""
from __future__ import annotations

from datetime import date

from estoque import Estoque, Lote, ModeloCesta, Produto
from pessoas import Doador, Familia


class Doacao:
    """Entrada de itens feita por um doador; gera os lotes que vão para o estoque."""

    _proximo_id = 1

    def __init__(self, doador: Doador, data: date | None = None, id: int | None = None):
        if id is None:
            id = Doacao._proximo_id
        Doacao._proximo_id = max(Doacao._proximo_id, id + 1)
        self.__id = id
        self.doador = doador                 # associação Doacao -> Doador
        self.data = data or date.today()
        self.__lotes: list[Lote] = []

    def get_id(self) -> int:
        return self.__id

    def adicionar_item(self, produto: Produto, qtd: float, validade: date) -> Lote:
        lote = Lote(produto, qtd, validade, self.data)
        self.__lotes.append(lote)
        return lote

    def adicionar_lote(self, lote: Lote) -> None:
        """Religa um lote já existente (usado ao carregar o JSON)."""
        self.__lotes.append(lote)

    def registrar(self, estoque: Estoque) -> None:
        """Envia os lotes ao estoque e inclui a doação no histórico do doador (dependência de Estoque)."""
        if not self.__lotes:
            raise ValueError("A doação não tem itens.")
        for lote in self.__lotes:
            estoque.adicionar_lote(lote)
        self.doador.registrar_doacao(self)

    def total_itens(self) -> float:
        return sum(l.quantidade_inicial for l in self.__lotes)

    def get_lotes(self) -> list[Lote]:
        return list(self.__lotes)

    def to_dict(self) -> dict:
        return {"id": self.__id, "doador_id": self.doador.get_id(), "data": self.data.isoformat(),
                "lotes": [l.get_id() for l in self.__lotes]}


class Entrega:
    """Cesta entregue a uma família; dá baixa no estoque pela regra FEFO."""

    _proximo_id = 1

    def __init__(self, familia: Familia, modelo: ModeloCesta, data: date | None = None,
                 id: int | None = None, itens: list[tuple[Produto, float]] | None = None):
        if id is None:
            id = Entrega._proximo_id
        Entrega._proximo_id = max(Entrega._proximo_id, id + 1)
        self.__id = id
        self.familia = familia
        self.modelo = modelo
        self.data = data or date.today()
        self.__itens: list[tuple[Produto, float]] = list(itens or [])

    def get_id(self) -> int:
        return self.__id

    def montar(self, estoque: Estoque) -> bool:
        """Retira os itens do modelo (FEFO). Se faltar qualquer item, devolve False e não baixa nada."""
        if estoque.faltante(self.modelo) or not self.modelo.listar_itens():
            return False
        for produto, qtd in self.modelo.listar_itens():
            estoque.retirar(produto, qtd)
            self.__itens.append((produto, qtd))
        self.familia.registrar_entrega(self)
        return True

    def total_itens(self) -> float:
        return sum(q for _, q in self.__itens)

    def get_itens(self) -> list[tuple[Produto, float]]:
        return list(self.__itens)

    def to_dict(self) -> dict:
        return {"id": self.__id, "familia_id": self.familia.get_id(), "data": self.data.isoformat(),
                "modelo": self.modelo.nome,
                "itens": [{"produto_id": p.get_id(), "quantidade": q} for p, q in self.__itens]}
