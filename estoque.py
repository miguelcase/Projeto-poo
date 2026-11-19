"""Módulo Estoque: Produto, Lote, Estoque e ModeloCesta (responsável: Miguel Pires)."""
from __future__ import annotations

from datetime import date


class Produto:
    """Item que pode ser doado e entregue (ex.: Arroz 5 kg, categoria grãos)."""

    _proximo_id = 1

    def __init__(self, nome: str, categoria: str, unidade: str, id: int | None = None):
        if not nome.strip() or not categoria.strip():
            raise ValueError("Nome e categoria são obrigatórios.")
        if id is None:
            id = Produto._proximo_id
        Produto._proximo_id = max(Produto._proximo_id, id + 1)
        self.__id = id
        self.nome = nome.strip()
        self.categoria = categoria.strip().lower()
        self.unidade = unidade.strip().lower() or "un"

    def get_id(self) -> int:
        return self.__id

    def validar_quantidade(self, qtd: float) -> None:
        """Quantidade maior que 0 e inteira para produto contado por unidade (não existe 2,5 sabonetes)."""
        if qtd <= 0:
            raise ValueError("A quantidade deve ser maior que 0.")
        if self.unidade == "un" and not float(qtd).is_integer():
            raise ValueError(f"{self.nome} é contado por unidade: use um número inteiro.")

    def to_dict(self) -> dict:
        return {"id": self.__id, "nome": self.nome, "categoria": self.categoria, "unidade": self.unidade}

    def __str__(self) -> str:
        return f"{self.nome} ({self.categoria})"


class Lote:
    """Quantidade de um produto com a mesma validade. É a unidade que o estoque controla."""

    _proximo_id = 1

    def __init__(self, produto: Produto, quantidade: float, validade: date,
                 data_entrada: date | None = None, id: int | None = None):
        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que 0.")
        if id is None:
            id = Lote._proximo_id
        Lote._proximo_id = max(Lote._proximo_id, id + 1)
        self.__id = id
        self.produto = produto                     # associação Lote -> Produto
        self.__quantidade = float(quantidade)      # saldo atual: só muda por retirar()
        self.quantidade_inicial = float(quantidade)
        self.validade = validade
        self.data_entrada = data_entrada or date.today()

    def get_id(self) -> int:
        return self.__id

    def get_quantidade(self) -> float:
        return self.__quantidade

    def dias_para_vencer(self, hoje: date | None = None) -> int:
        return (self.validade - (hoje or date.today())).days

    def esta_vencido(self, hoje: date | None = None) -> bool:
        return self.dias_para_vencer(hoje) < 0

    def retirar(self, qtd: float) -> float:
        """Reduz o saldo em até qtd e devolve o quanto realmente saiu (o saldo nunca fica negativo)."""
        saiu = min(qtd, self.__quantidade)
        self.__quantidade -= saiu
        return saiu

    def devolver(self, qtd: float) -> None:
        """Estorno de entrega: o item volta para o lote de onde saiu (nunca passa da quantidade inicial)."""
        if qtd <= 0 or self.__quantidade + qtd > self.quantidade_inicial + 1e-9:
            raise ValueError(f"Lote {self.__id} não pode receber {qtd:g} de volta.")
        self.__quantidade += qtd

    def to_dict(self) -> dict:
        return {"id": self.__id, "produto_id": self.produto.get_id(), "quantidade": self.__quantidade,
                "quantidade_inicial": self.quantidade_inicial, "validade": self.validade.isoformat(),
                "data_entrada": self.data_entrada.isoformat()}


class ModeloCesta:
    """Define o que vai em uma cesta padrão (produtos e quantidades)."""

    def __init__(self, nome: str):
        self.nome = nome
        self.__itens: dict[Produto, float] = {}

    def adicionar_item(self, produto: Produto, qtd: float) -> None:
        if qtd <= 0:
            raise ValueError("A quantidade deve ser maior que 0.")
        self.__itens[produto] = float(qtd)

    def remover_item(self, produto: Produto) -> None:
        self.__itens.pop(produto, None)

    def listar_itens(self) -> list[tuple[Produto, float]]:
        return list(self.__itens.items())

    def to_dict(self) -> dict:
        return {"nome": self.nome, "itens": [{"produto_id": p.get_id(), "quantidade": q} for p, q in self.__itens.items()]}


class Estoque:
    """Conjunto de todos os lotes. Aplica a regra FEFO, calcula saldos e gera alertas de validade."""

    def __init__(self):
        self.__lotes: list[Lote] = []   # composição: o estoque é formado por lotes
        self._dias_alerta = 15

    def adicionar_lote(self, lote: Lote) -> None:
        self.__lotes.append(lote)

    def remover_lote(self, lote: Lote) -> None:
        """Usado só no estorno de doação (o lote nunca foi usado)."""
        self.__lotes.remove(lote)

    def get_lotes(self) -> list[Lote]:
        """Lotes com saldo (cópia da lista, para consulta)."""
        return [l for l in self.__lotes if l.get_quantidade() > 0]

    def __ordenar_fefo(self, produto: Produto) -> list[Lote]:
        """Lotes válidos e com saldo do produto, do que vence primeiro ao que vence por último."""
        validos = [l for l in self.get_lotes() if l.produto is produto and not l.esta_vencido()]
        return sorted(validos, key=lambda l: l.validade)

    def previa_retirada(self, produto: Produto, qtd: float) -> list[tuple[Lote, float]]:
        """Mostra de quais lotes sairia qtd pela regra FEFO, sem mexer no estoque."""
        if qtd > self.saldo(produto):
            raise ValueError(f"Saldo insuficiente de {produto.nome}.")
        plano, falta = [], qtd
        for lote in self.__ordenar_fefo(produto):
            if falta <= 0:
                break
            usar = min(falta, lote.get_quantidade())
            plano.append((lote, usar))
            falta -= usar
        return plano

    def retirar(self, produto: Produto, qtd: float) -> list[tuple[Lote, float]]:
        """Dá baixa por FEFO e devolve os lotes usados com a quantidade tirada de cada um."""
        plano = self.previa_retirada(produto, qtd)
        for lote, usar in plano:
            lote.retirar(usar)
        return plano

    def saldo(self, produto: Produto) -> float:
        return sum(l.get_quantidade() for l in self.__ordenar_fefo(produto))

    def proximo_vencimento(self, produto: Produto) -> date | None:
        """Validade do lote que sai primeiro (None se não há saldo válido)."""
        fefo = self.__ordenar_fefo(produto)
        return fefo[0].validade if fefo else None

    def saldo_por_categoria(self) -> dict[str, float]:
        totais: dict[str, float] = {}
        for lote in self.get_lotes():
            if not lote.esta_vencido():
                totais[lote.produto.categoria] = totais.get(lote.produto.categoria, 0) + lote.get_quantidade()
        return totais

    def lotes_a_vencer(self, dias: int | None = None) -> list[Lote]:
        dias = self._dias_alerta if dias is None else dias
        perto = [l for l in self.get_lotes() if 0 <= l.dias_para_vencer() <= dias]
        return sorted(perto, key=lambda l: l.validade)

    def lotes_vencidos(self) -> list[Lote]:
        return sorted((l for l in self.get_lotes() if l.esta_vencido()), key=lambda l: l.validade)

    def descartar_vencidos(self) -> list[tuple[Lote, float]]:
        """Zera os lotes vencidos (descarte) e devolve o que foi descartado."""
        return [(l, l.retirar(l.get_quantidade())) for l in self.lotes_vencidos()]

    def cestas_possiveis(self, modelo: ModeloCesta) -> int:
        itens = modelo.listar_itens()
        if not itens:
            return 0
        return min(int(self.saldo(p) // q) for p, q in itens)

    def faltante(self, modelo: ModeloCesta, cestas: int = 1) -> dict[Produto, float]:
        """O que falta para montar `cestas` cestas (padrão: uma)."""
        falta = {}
        for produto, qtd in modelo.listar_itens():
            precisa = qtd * cestas - self.saldo(produto)
            if precisa > 0:
                falta[produto] = precisa
        return falta

    def to_dict(self) -> list[dict]:
        # Guarda também lotes zerados, porque as doações antigas apontam para eles.
        return [l.to_dict() for l in self.__lotes]
