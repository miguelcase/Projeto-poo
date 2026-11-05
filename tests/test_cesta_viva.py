"""Testes automatizados do Cesta Viva. Rodar na pasta do projeto: python -m unittest discover -s tests -v"""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from estoque import Estoque, Lote, ModeloCesta, Produto
from movimentacoes import Doacao, Entrega
from pessoas import Doador, Familia, Pessoa
from relatorio import Relatorio
from sistema import Sistema

HOJE = date.today()


def dias(n: int) -> date:
    return HOJE + timedelta(days=n)


class TestEstoque(unittest.TestCase):
    def setUp(self):
        self.arroz = Produto("Arroz 5 kg", "grãos", "un")
        self.oleo = Produto("Óleo 900 ml", "óleos", "un")
        self.estoque = Estoque()
        self.lote_longe = Lote(self.arroz, 10, dias(90))
        self.lote_perto = Lote(self.arroz, 5, dias(10))
        self.lote_vencido = Lote(self.arroz, 7, dias(-3))
        for lote in (self.lote_longe, self.lote_perto, self.lote_vencido):
            self.estoque.adicionar_lote(lote)

    def test_saldo_ignora_vencidos(self):
        self.assertEqual(self.estoque.saldo(self.arroz), 15)

    def test_retirada_segue_fefo(self):
        usados = self.estoque.retirar(self.arroz, 8)
        self.assertEqual([(l.get_id(), q) for l, q in usados],
                         [(self.lote_perto.get_id(), 5), (self.lote_longe.get_id(), 3)])
        self.assertEqual(self.lote_perto.get_quantidade(), 0)
        self.assertEqual(self.lote_longe.get_quantidade(), 7)
        self.assertEqual(self.lote_vencido.get_quantidade(), 7)   # vencido nunca sai na cesta

    def test_retirada_maior_que_saldo_da_erro_e_nao_mexe(self):
        with self.assertRaises(ValueError):
            self.estoque.retirar(self.arroz, 16)
        self.assertEqual(self.estoque.saldo(self.arroz), 15)

    def test_alertas_de_validade(self):
        self.assertEqual(self.estoque.lotes_a_vencer(), [self.lote_perto])
        self.assertEqual(self.estoque.lotes_vencidos(), [self.lote_vencido])

    def test_cestas_possiveis_e_faltante(self):
        modelo = ModeloCesta("Cesta Padrão")
        modelo.adicionar_item(self.arroz, 2)
        modelo.adicionar_item(self.oleo, 1)
        self.assertEqual(self.estoque.cestas_possiveis(modelo), 0)       # sem óleo, nenhuma cesta
        self.estoque.adicionar_lote(Lote(self.oleo, 4, dias(60)))
        self.assertEqual(self.estoque.cestas_possiveis(modelo), 4)       # óleo limita: 4 cestas
        self.assertEqual(self.estoque.faltante(modelo, 5), {self.oleo: 1})

    def test_lote_nao_aceita_quantidade_zero(self):
        with self.assertRaises(ValueError):
            Lote(self.arroz, 0, dias(30))

    def test_atributo_privado_nao_e_acessivel(self):
        with self.assertRaises(AttributeError):
            self.lote_longe.__quantidade
        self.assertEqual(self.lote_longe.get_quantidade(), 10)


class TestPessoas(unittest.TestCase):
    def test_pessoa_e_abstrata(self):
        with self.assertRaises(TypeError):
            Pessoa("Alguém", "51999990000")

    def test_heranca_e_polimorfismo(self):
        doador = Doador("Mercado Bom Preço", "5133334444", "PJ", "12.345.678/0001-90")
        familia = Familia("Silva", "51999990000", "Maria Silva", 4, "Rua das Flores, 120")
        self.assertIsInstance(doador, Pessoa)
        self.assertIsInstance(familia, Pessoa)
        self.assertEqual([p.descricao() for p in (doador, familia)],
                         ["Mercado Bom Preço (PJ)", "Família Silva, 4 pessoas"])

    def test_validacoes(self):
        with self.assertRaises(ValueError):
            Doador("Ana", "51999990000", "PF", "123")          # CPF curto
        with self.assertRaises(ValueError):
            Familia("Souza", "5199", "João", 3, "Rua A")         # telefone sem DDD
        with self.assertRaises(ValueError):
            Familia("Souza", "51999990000", "João", 0, "Rua A")  # família sem pessoas

    def test_doador_da_planilha_fica_incompleto(self):
        doador = Doador("Padaria Central", "", "", "")
        self.assertEqual(doador.descricao(), "Padaria Central (incompleto)")
        with self.assertRaises(ValueError):
            doador.alterar_documento("PJ", "123")                # CNPJ curto é recusado
        doador.alterar_documento("PJ", "98.765.432/0001-10")
        self.assertEqual(doador.descricao(), "Padaria Central (PJ)")

    def test_documento_mascarado(self):
        doador = Doador("Ana", "51999990000", "PF", "123.456.789-09")
        self.assertEqual(doador.documento_mascarado(), "123******09")


class TestMovimentacoes(unittest.TestCase):
    def setUp(self):
        self.arroz = Produto("Arroz 5 kg", "grãos", "un")
        self.feijao = Produto("Feijão 1 kg", "grãos", "un")
        self.modelo = ModeloCesta("Cesta Padrão")
        self.modelo.adicionar_item(self.arroz, 1)
        self.modelo.adicionar_item(self.feijao, 2)
        self.estoque = Estoque()
        self.doador = Doador("Maria Souza", "51988887777", "PF", "12345678909")
        self.familia = Familia("Silva", "51999990000", "Maria Silva", 4, "Rua das Flores, 120")

    def test_doacao_abastece_estoque_e_historico(self):
        doacao = Doacao(self.doador)
        doacao.adicionar_item(self.arroz, 10, dias(100))
        doacao.adicionar_item(self.feijao, 20, dias(100))
        doacao.registrar(self.estoque)
        self.assertEqual(self.estoque.saldo(self.feijao), 20)
        self.assertEqual(self.doador.total_doado(), 30)

    def test_entrega_sem_estoque_nao_baixa_nada(self):
        doacao = Doacao(self.doador)
        doacao.adicionar_item(self.arroz, 10, dias(100))    # tem arroz, mas não tem feijão
        doacao.registrar(self.estoque)
        entrega = Entrega(self.familia, self.modelo)
        self.assertFalse(entrega.montar(self.estoque))
        self.assertEqual(self.estoque.saldo(self.arroz), 10)
        self.assertIsNone(self.familia.ultima_entrega())

    def test_entrega_completa(self):
        doacao = Doacao(self.doador)
        doacao.adicionar_item(self.arroz, 3, dias(100))
        doacao.adicionar_item(self.feijao, 6, dias(100))
        doacao.registrar(self.estoque)
        entrega = Entrega(self.familia, self.modelo)
        self.assertTrue(entrega.montar(self.estoque))
        self.assertEqual(self.estoque.cestas_possiveis(self.modelo), 2)
        self.assertEqual(self.familia.ultima_entrega(), HOJE)
        self.assertEqual(self.doador.total_doado(), 9)       # histórico da doação não diminui com a saída


class TestSistema(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.antiga = os.getcwd()
        os.chdir(self.pasta.name)

    def tearDown(self):
        os.chdir(self.antiga)
        self.pasta.cleanup()

    def importar(self, sistema, caminho="planilha.csv"):
        with redirect_stdout(io.StringIO()):          # esconde o resumo impresso na tela
            return sistema.importar_csv(caminho)

    def escrever_csv(self, linhas):
        with open("planilha.csv", "w", encoding="utf-8") as f:
            f.write("produto,categoria,unidade,quantidade,validade,doador,data_doacao\n" + "\n".join(linhas) + "\n")

    def test_importa_csv_e_ignora_linhas_invalidas(self):
        self.escrever_csv(["Arroz 5 kg,grãos,un,30,15/03/2030,Mercado Bom Preço,12/05/2026",
                           "Feijão 1 kg,grãos,un,abc,15/03/2030,Maria Souza,12/05/2026",
                           "Leite 1 L,laticínios,un,12,31/02/2030,Padaria Central,03/06/2026",
                           "Óleo 900 ml,óleos,un,6,15/03/27,João Lima,03/06/2026"])     # ano com 2 dígitos
        sistema = Sistema(os.path.join("dados", "teste.json"))
        self.assertEqual(self.importar(sistema), 1)
        with open(os.path.join("saida", "erros_importacao.txt"), encoding="utf-8") as f:
            erros = f.read()
        self.assertIn("linha 3: quantidade não é número", erros)
        self.assertIn("linha 4: data inválida", erros)
        self.assertIn("linha 5: data inválida", erros)

    def test_salvar_e_carregar_json(self):
        self.escrever_csv(["Arroz 5 kg,grãos,un,30,15/03/2030,Mercado Bom Preço,12/05/2026"])
        sistema = Sistema(os.path.join("dados", "teste.json"))
        self.importar(sistema)
        arroz = next(p for p in sistema.get_produtos() if p.nome == "Arroz 5 kg")
        sistema.get_estoque().retirar(arroz, 4)
        sistema.salvar()
        novo = Sistema(os.path.join("dados", "teste.json"))
        arroz_novo = next(p for p in novo.get_produtos() if p.nome == "Arroz 5 kg")
        self.assertEqual(novo.get_estoque().saldo(arroz_novo), 26)
        self.assertEqual(novo.get_doadores()[0].total_doado(), 30)
        self.assertEqual(len(novo.get_modelo_cesta().listar_itens()), 7)

    def test_relatorio_gera_csv_e_grafico(self):
        self.escrever_csv(["Arroz 5 kg,grãos,un,30,15/03/2030,Mercado Bom Preço,12/05/2026"])
        sistema = Sistema(os.path.join("dados", "teste.json"))
        self.importar(sistema)
        relatorio = Relatorio(sistema)
        self.assertTrue(os.path.exists(relatorio.exportar_csv(relatorio.estoque_atual(), "estoque")))
        try:
            self.assertTrue(os.path.exists(relatorio.grafico_estoque_categoria()))
        except RuntimeError:
            self.skipTest("Matplotlib não instalado")


if __name__ == "__main__":
    unittest.main()
