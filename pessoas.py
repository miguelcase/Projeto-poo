"""Módulo Pessoas: Pessoa (abstrata), Doador e Familia (responsável: Arthur Sacomorri)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from movimentacoes import Doacao, Entrega

# DDDs existentes no Brasil (Anatel)
DDDS = {11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 24, 27, 28, 31, 32, 33, 34, 35, 37, 38,
        41, 42, 43, 44, 45, 46, 47, 48, 49, 51, 53, 54, 55, 61, 62, 63, 64, 65, 66, 67, 68, 69,
        71, 73, 74, 75, 77, 79, 81, 82, 83, 84, 85, 86, 87, 88, 89, 91, 92, 93, 94, 95, 96, 97, 98, 99}


class Pessoa(ABC):
    """Dados comuns de Doador e Familia. Não é instanciada diretamente."""

    _proximo_id = 1

    def __init__(self, nome: str, telefone: str, id: int | None = None):
        if not nome.strip():
            raise ValueError("O nome não pode ficar vazio.")
        telefone = "".join(c for c in telefone if c.isdigit())
        # ao carregar o JSON (id informado) só confere o tamanho: arquivo salvo antes da regra do DDD continua abrindo
        valido = Pessoa.validar_telefone(telefone) if id is None else len(telefone) in (10, 11)
        if telefone and not valido:
            raise ValueError("Telefone inválido: DDD + número, ex.: (51) 99999-0000.")
        classe = type(self)   # cada subclasse tem sua própria numeração
        if id is None:
            id = classe._proximo_id
        classe._proximo_id = max(classe._proximo_id, id + 1)
        self.__id = id
        self.nome = nome.strip()
        self.telefone = telefone

    def get_id(self) -> int:
        return self.__id

    @abstractmethod
    def descricao(self) -> str:
        """Resumo em uma linha; cada subclasse escreve o seu."""

    def __str__(self) -> str:
        return self.descricao()

    def to_dict(self) -> dict:
        return {"id": self.__id, "nome": self.nome, "telefone": self.telefone}

    @staticmethod
    def validar_telefone(tel: str) -> bool:
        """DDD que existe; fixo (10 dígitos) começa com 2 a 5 e celular (11 dígitos) com 9."""
        if not tel.isdigit() or len(tel) not in (10, 11) or int(tel[:2]) not in DDDS:
            return False
        return tel[2] == "9" if len(tel) == 11 else tel[2] in "2345"


class Doador(Pessoa):
    """Pessoa física ou empresa que doa alimentos."""

    _proximo_id = 1

    def __init__(self, nome: str, telefone: str, tipo: str, documento: str, id: int | None = None):
        super().__init__(nome, telefone, id)
        self.tipo = tipo.strip().upper()
        self.__documento = "".join(c for c in documento if c.isdigit())
        # enxuto: tipo e documento vazios só para doadores vindos da planilha antiga → completar no menu Doadores
        if (self.tipo or self.__documento) and (self.tipo not in ("PF", "PJ") or not self.__validar_documento()):
            raise ValueError("Tipo deve ser PF (CPF com 11 dígitos) ou PJ (CNPJ com 14 dígitos).")
        self.__doacoes: list[Doacao] = []

    def __validar_documento(self) -> bool:
        # enxuto: confere só a quantidade de dígitos, não os dígitos verificadores
        return len(self.__documento) == (11 if self.tipo == "PF" else 14)

    def alterar_documento(self, tipo: str, documento: str) -> None:
        """Completa ou corrige o documento; só aceita se passar na validação."""
        antigo = (self.tipo, self.__documento)
        self.tipo, self.__documento = tipo.strip().upper(), "".join(c for c in documento if c.isdigit())
        if self.tipo not in ("PF", "PJ") or not self.__validar_documento():
            self.tipo, self.__documento = antigo
            raise ValueError("CPF deve ter 11 dígitos e CNPJ 14 dígitos.")

    def registrar_doacao(self, doacao: Doacao) -> None:
        self.__doacoes.append(doacao)

    def remover_doacao(self, doacao: Doacao) -> None:
        """Usado só no estorno."""
        self.__doacoes.remove(doacao)

    def get_doacoes(self) -> list[Doacao]:
        return list(self.__doacoes)

    def total_doado(self) -> float:
        return sum(d.total_itens() for d in self.__doacoes)

    def documento_mascarado(self) -> str:
        doc = self.__documento
        if not doc:
            return "não informado"
        return doc[:3] + "*" * (len(doc) - 5) + doc[-2:]

    def descricao(self) -> str:
        return f"{self.nome} ({self.tipo or 'incompleto'})"

    def to_dict(self) -> dict:
        return {**super().to_dict(), "tipo": self.tipo, "documento": self.__documento}


class Familia(Pessoa):
    """Família atendida pelo banco de alimentos (o nome herdado é o nome da família)."""

    _proximo_id = 1

    def __init__(self, nome: str, telefone: str, responsavel: str, num_pessoas: int,
                 endereco: str, id: int | None = None):
        super().__init__(nome, telefone, id)
        if num_pessoas < 1:
            raise ValueError("A família precisa ter pelo menos 1 pessoa.")
        self.responsavel = responsavel.strip()
        self.num_pessoas = num_pessoas
        self.endereco = endereco.strip()
        self.__entregas: list[Entrega] = []

    def registrar_entrega(self, entrega: Entrega) -> None:
        self.__entregas.append(entrega)

    def remover_entrega(self, entrega: Entrega) -> None:
        """Usado só no estorno."""
        self.__entregas.remove(entrega)

    def ultima_entrega(self) -> date | None:
        return max((e.data for e in self.__entregas), default=None)

    def dias_desde_ultima_entrega(self, hoje: date | None = None) -> int | None:
        ultima = self.ultima_entrega()
        return ((hoje or date.today()) - ultima).days if ultima else None

    def historico(self) -> list[Entrega]:
        return list(self.__entregas)

    def descricao(self) -> str:
        return f"Família {self.nome}, {self.num_pessoas} pessoas"

    def to_dict(self) -> dict:
        return {**super().to_dict(), "responsavel": self.responsavel,
                "num_pessoas": self.num_pessoas, "endereco": self.endereco}
