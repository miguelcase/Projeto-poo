"""Sistema: menu, leitura do teclado, persistência em JSON e importação do CSV (responsável: João Zamora)."""
from __future__ import annotations

import csv
import io
import json
import os
from datetime import date, datetime

from estoque import Estoque, Lote, ModeloCesta, Produto
from movimentacoes import Doacao, Entrega
from pessoas import Doador, Familia
from relatorio import Relatorio

ARQUIVO_ERROS = os.path.join("saida", "erros_importacao.txt")
CABECALHO_CSV = ["produto", "categoria", "unidade", "quantidade", "validade", "doador"]


class Sistema:
    """Controlador do programa: único que fala com o teclado e com os arquivos JSON/CSV."""

    def __init__(self, arquivo_dados: str = os.path.join("dados", "cesta_viva.json")):
        self.__estoque = Estoque()
        self.__produtos: list[Produto] = []
        self.__doadores: list[Doador] = []
        self.__familias: list[Familia] = []
        self.__modelo_cesta = ModeloCesta("Cesta Padrão")
        self.__historico: list[Doacao | Entrega] = []
        self._arquivo_dados = arquivo_dados
        if not self.carregar():
            self.__criar_padrao()

    # ---------- leitura pelo Relatorio ----------
    def get_estoque(self) -> Estoque:
        return self.__estoque

    def get_produtos(self) -> list[Produto]:
        return list(self.__produtos)

    def get_doadores(self) -> list[Doador]:
        return list(self.__doadores)

    def get_familias(self) -> list[Familia]:
        return list(self.__familias)

    def get_historico(self) -> list[Doacao | Entrega]:
        return list(self.__historico)

    def get_modelo_cesta(self) -> ModeloCesta:
        return self.__modelo_cesta

    # ---------- laço principal ----------
    def executar(self, relatorio: Relatorio) -> None:
        acoes = {"1": self.menu_estoque, "2": self.registrar_doacao, "3": self.menu_familias,
                 "4": self.menu_doadores, "5": lambda: self.menu_relatorios(relatorio), "6": self.menu_importar}
        try:
            while True:
                self.__exibir_menu()
                opcao = self.__ler_entrada("Escolha uma opção: ", "escolha", list("0123456"))
                if opcao == "0":
                    break
                try:
                    acoes[opcao]()
                except (ValueError, RuntimeError, OSError) as erro:
                    print(f"[ERRO] {erro}")
        except (KeyboardInterrupt, EOFError):
            print("\nEncerrando...")
        self.salvar()
        print(f"Dados salvos em {self._arquivo_dados}. Até logo!")

    def __exibir_menu(self) -> None:
        print("\n=========== CESTA VIVA ===========")
        print("1. Estoque (ver saldo, alertas de validade)")
        print("2. Registrar doação")
        print("3. Famílias e entrega de cestas")
        print("4. Doadores")
        print("5. Relatórios e gráficos")
        print("6. Importar planilha antiga (CSV)")
        print("0. Salvar e sair")

    def __ler_entrada(self, msg: str, tipo: str = "texto", opcoes=None):
        """Lê e valida o teclado; repete a pergunta até a resposta ser válida."""
        while True:
            resp = input(msg).strip()
            if tipo == "texto_opcional":
                return resp
            if tipo == "escolha":
                if resp.upper() in opcoes:
                    return resp.upper()
                print("[ERRO] Opção inválida.")
            elif not resp:
                print("[ERRO] Este campo não pode ficar vazio.")
            elif tipo == "texto":
                return resp
            elif tipo == "numero":
                try:
                    valor = float(resp.replace(",", "."))
                except ValueError:
                    print("[ERRO] Digite apenas números.")
                    continue
                if valor > 0:
                    return valor
                print("[ERRO] A quantidade deve ser maior que 0.")
            elif tipo == "inteiro":
                if resp.isdigit() and int(resp) > 0:
                    return int(resp)
                print("[ERRO] Digite um número inteiro maior que 0.")
            elif tipo == "data":
                try:
                    return self.__data(resp)
                except ValueError:
                    print("[ERRO] Data inválida. Use dd/mm/aaaa (ano com 4 dígitos).")
            elif tipo == "sn":
                if resp.lower() in ("s", "n"):
                    return resp.lower() == "s"
                print("[ERRO] Responda s ou n.")
            elif tipo == "digitos":
                digitos = "".join(c for c in resp if c.isdigit())
                if len(digitos) in opcoes:
                    return digitos
                print(f"[ERRO] Digite {' ou '.join(map(str, opcoes))} dígitos.")

    def __escolher(self, itens: list, rotulo: str, permitir_novo: bool = False):
        """Pede o nº de um item da lista ('l' lista tudo; 'n' devolve None para cadastrar um novo)."""
        if not itens and not permitir_novo:
            print(f"[AVISO] Nenhum(a) {rotulo.lower()} cadastrado(a).")
            return None
        extra = ", 'n' para novo" if permitir_novo else ""
        while True:
            resp = input(f"{rotulo} (nº{extra}, 'l' lista): ").strip().lower()
            if resp == "l":
                for item in itens:
                    print(f"  {item.get_id():>3}  {item}")
            elif permitir_novo and resp == "n":
                return None
            elif not resp.isdigit():
                print("[ERRO] Digite apenas números.")
            else:
                achado = next((i for i in itens if i.get_id() == int(resp)), None)
                if achado:
                    print(f"  > {achado}")
                    return achado
                print(f"[ERRO] {rotulo} nº {resp} não existe.")

    # ---------- 1. Estoque ----------
    def menu_estoque(self) -> None:
        while True:
            print("\n============== ESTOQUE ==============")
            print(f"{'Produto':<22}{'Categ.':<12}{'Saldo':>6}  Vence em")
            for p in sorted(self.__produtos, key=lambda p: (p.categoria, p.nome)):
                vence = self.__estoque.proximo_vencimento(p)
                vence = vence.strftime("%d/%m/%Y") if vence else "-"
                print(f"{p.nome[:21]:<22}{p.categoria[:11]:<12}{self.__estoque.saldo(p):>6g}  {vence}")
            print("\nALERTAS DE VALIDADE")
            alertas = [(l, f"VENCIDO há {-l.dias_para_vencer()} dias", "X") for l in self.__estoque.lotes_vencidos()]
            alertas += [(l, f"vence em {l.dias_para_vencer()} dias", "!") for l in self.__estoque.lotes_a_vencer()]
            for lote, texto, marca in alertas:
                print(f" [{marca}] {lote.produto.nome[:15]:<16}lote {lote.get_id():<4} {texto}")
            if not alertas:
                print(" Nenhum lote vencido ou perto de vencer.")
            n = self.__estoque.cestas_possiveis(self.__modelo_cesta)
            print(f"\nCestas completas possíveis: {n}")
            falta = self.__estoque.faltante(self.__modelo_cesta, n + 1)
            print(f"Para a {n + 1}ª cesta falta: "
                  + (", ".join(f"{p.nome} ({q:g})" for p, q in falta.items()) or "definir o modelo da cesta"))
            print("\n1. Ver lotes  2. Produtos  3. Modelo da cesta  4. Descartar vencidos  0. Voltar")
            opcao = self.__ler_entrada("Escolha uma opção: ", "escolha", list("01234"))
            if opcao == "0":
                return
            {"1": self.__ver_lotes, "2": self.menu_produtos, "3": self.menu_modelo_cesta,
             "4": self.__descartar_vencidos}[opcao]()

    def __ver_lotes(self) -> None:
        print(f"\n{'Lote':>4}  {'Produto':<22}{'Saldo':>6}  {'Validade':<11} Entrada")
        for l in sorted(self.__estoque.get_lotes(), key=lambda l: l.validade):
            print(f"{l.get_id():>4}  {l.produto.nome[:21]:<22}{l.get_quantidade():>6g}  "
                  f"{l.validade.strftime('%d/%m/%Y'):<11} {l.data_entrada.strftime('%d/%m/%Y')}"
                  + ("  VENCIDO" if l.esta_vencido() else ""))

    def __descartar_vencidos(self) -> None:
        print("\n========== DESCARTAR VENCIDOS ==========")
        vencidos = self.__estoque.lotes_vencidos()
        if not vencidos:
            print("Nenhum lote vencido.")
            return
        for l in vencidos:
            print(f"  lote {l.get_id()}: {l.produto.nome} ({l.get_quantidade():g}) venceu em {l.validade.strftime('%d/%m/%Y')}")
        if self.__ler_entrada(f"Descartar {len(vencidos)} lote(s)? (s/n): ", "sn"):
            descartados = self.__estoque.descartar_vencidos()
            print(f"{sum(q for _, q in descartados):g} itens descartados.")
            self.salvar()

    def menu_produtos(self) -> None:
        while True:
            print("\n============== PRODUTOS ==============")
            print(f"{'Nº':>3}  {'Produto':<26}{'Categoria':<13}Unid.")
            for p in sorted(self.__produtos, key=lambda p: p.get_id()):
                print(f"{p.get_id():>3}  {p.nome[:25]:<26}{p.categoria[:12]:<13}{p.unidade}")
            print("\n1. Cadastrar  2. Editar  3. Remover  4. Renomear categoria  0. Voltar")
            opcao = self.__ler_entrada("Escolha uma opção: ", "escolha", list("01234"))
            if opcao == "0":
                return
            {"1": self.cadastrar_produto, "2": self.__editar_produto, "3": self.__remover_produto,
             "4": self.__renomear_categoria}[opcao]()
            self.salvar()

    def cadastrar_produto(self) -> Produto | None:
        print("\n========== CADASTRAR PRODUTO ==========")
        nome = self.__ler_entrada("Nome (ex.: Arroz 5 kg): ")
        if self.__produto_por_nome(nome):
            print("[ERRO] Já existe um produto com esse nome.")
            return None
        produto = Produto(nome, self.__ler_entrada("Categoria (ex.: grãos): "),
                          self.__ler_entrada("Unidade (un, kg, L): "))
        self.__produtos.append(produto)
        print(f"Produto nº {produto.get_id()} cadastrado: {produto}")
        return produto

    def __editar_produto(self) -> None:
        produto = self.__escolher(self.__produtos, "Produto")
        if not produto:
            return
        print("Deixe em branco para manter o valor atual.")
        produto.nome = self.__ler_entrada(f"Nome [{produto.nome}]: ", "texto_opcional") or produto.nome
        produto.categoria = (self.__ler_entrada(f"Categoria [{produto.categoria}]: ", "texto_opcional").lower()
                             or produto.categoria)
        produto.unidade = self.__ler_entrada(f"Unidade [{produto.unidade}]: ", "texto_opcional") or produto.unidade
        print(f"Produto atualizado: {produto}")

    def __remover_produto(self) -> None:
        produto = self.__escolher(self.__produtos, "Produto")
        if not produto:
            return
        em_uso = (any(l.produto is produto for m in self.__historico if isinstance(m, Doacao) for l in m.get_lotes())
                  or any(p is produto for p, _ in self.__modelo_cesta.listar_itens()))
        if em_uso:
            print("[ERRO] Este produto tem lotes no histórico ou está na cesta padrão; não pode ser removido.")
        elif self.__ler_entrada(f"Remover {produto}? (s/n): ", "sn"):
            self.__produtos.remove(produto)
            print("Produto removido.")

    def __renomear_categoria(self) -> None:
        categorias = sorted({p.categoria for p in self.__produtos})
        print("Categorias: " + ", ".join(categorias))
        atual = self.__ler_entrada("Categoria atual: ").lower()
        if atual not in categorias:
            print("[ERRO] Categoria não encontrada.")
            return
        nova = self.__ler_entrada("Novo nome: ").lower()
        for p in self.__produtos:
            if p.categoria == atual:
                p.categoria = nova
        print(f"Categoria '{atual}' renomeada para '{nova}'.")

    def menu_modelo_cesta(self) -> None:
        while True:
            print(f"\n========= MODELO: {self.__modelo_cesta.nome} =========")
            for p, q in self.__modelo_cesta.listar_itens():
                print(f"  {p.nome:<20} x{q:g}")
            print("\n1. Adicionar/alterar item  2. Remover item  0. Voltar")
            opcao = self.__ler_entrada("Escolha uma opção: ", "escolha", list("012"))
            if opcao == "0":
                return
            produto = self.__escolher(self.__produtos, "Produto")
            if produto and opcao == "1":
                self.__modelo_cesta.adicionar_item(produto, self.__ler_entrada("Quantidade por cesta: ", "numero"))
            elif produto:
                self.__modelo_cesta.remover_item(produto)
            self.salvar()

    # ---------- 2. Doação ----------
    def registrar_doacao(self) -> None:
        print("\n========== REGISTRAR DOAÇÃO ==========")
        doador = self.__escolher(self.__doadores, "Doador", permitir_novo=True) or self.cadastrar_doador()
        doacao = Doacao(doador)
        while True:
            produto = self.__escolher(self.__produtos, "Produto")
            if not produto:
                return
            qtd = self.__ler_entrada("Quantidade: ", "numero")
            validade = self.__ler_validade()
            doacao.adicionar_item(produto, qtd, validade)
            if not self.__ler_entrada("Adicionar outro item? (s/n): ", "sn"):
                break
        if not self.__ler_entrada(f"Confirmar doação de {doacao.total_itens():g} itens? (s/n): ", "sn"):
            print("Doação cancelada. Nada foi alterado.")
            return
        doacao.registrar(self.__estoque)
        self.__historico.append(doacao)
        self.salvar()
        print(f"\nDoação nº {doacao.get_id()} registrada em {doacao.data.strftime('%d/%m/%Y')}.")
        for l in doacao.get_lotes():
            print(f"  lote {l.get_id()}: {l.produto.nome} x{l.quantidade_inicial:g}  vence "
                  f"{l.validade.strftime('%d/%m/%Y')} | saldo agora: {self.__estoque.saldo(l.produto):g}")

    def __ler_validade(self) -> date:
        while True:
            validade = self.__ler_entrada("Validade (dd/mm/aaaa): ", "data")
            if validade >= date.today():
                return validade
            print("[AVISO] Esta data já passou.")
            if self.__ler_entrada("Registrar mesmo assim? (s/n): ", "sn"):
                return validade

    def cadastrar_doador(self) -> Doador:
        print("\n========== CADASTRAR DOADOR ==========")
        nome = self.__ler_entrada("Nome: ")
        tipo = self.__ler_entrada("Tipo (PF/PJ): ", "escolha", ["PF", "PJ"])
        documento = self.__ler_entrada("CPF (só dígitos): " if tipo == "PF" else "CNPJ (só dígitos): ",
                                       "digitos", (11,) if tipo == "PF" else (14,))
        telefone = self.__ler_entrada("Telefone (com DDD): ", "digitos", (10, 11))
        doador = Doador(nome, telefone, tipo, documento)
        self.__doadores.append(doador)
        self.salvar()
        print(f"Doador nº {doador.get_id()} cadastrado: {doador.descricao()}")
        return doador

    # ---------- 3. Famílias e entregas ----------
    def menu_familias(self) -> None:
        while True:
            print("\n====== FAMÍLIAS E ENTREGA DE CESTAS ======")
            print(f"{'Nº':>3}  {'Família':<32}Última entrega")
            for f in self.__familias:
                ultima = f.ultima_entrega()
                print(f"{f.get_id():>3}  {f.descricao()[:31]:<32}{ultima.strftime('%d/%m/%Y') if ultima else 'nunca'}")
            print("\n1. Cadastrar família  2. Registrar entrega  3. Histórico da família  0. Voltar")
            opcao = self.__ler_entrada("Escolha uma opção: ", "escolha", list("0123"))
            if opcao == "0":
                return
            {"1": self.cadastrar_familia, "2": self.registrar_entrega, "3": self.__historico_familia}[opcao]()

    def cadastrar_familia(self) -> Familia:
        print("\n========== CADASTRAR FAMÍLIA ==========")
        familia = Familia(self.__ler_entrada("Nome da família: "),
                          self.__ler_entrada("Telefone (com DDD): ", "digitos", (10, 11)),
                          self.__ler_entrada("Responsável: "),
                          self.__ler_entrada("Nº de pessoas: ", "inteiro"),
                          self.__ler_entrada("Endereço: "))
        self.__familias.append(familia)
        self.salvar()
        print(f"\nFamília nº {familia.get_id()} cadastrada: {familia.descricao()}")
        return familia

    def registrar_entrega(self) -> None:
        print("\n========== ENTREGAR CESTA ==========")
        familia = self.__escolher(self.__familias, "Família")
        if not familia:
            return
        ultima = familia.ultima_entrega()
        print(f"  > Última entrega: {ultima.strftime('%d/%m/%Y') if ultima else 'nunca recebeu'}")
        print(f"Modelo: {self.__modelo_cesta.nome}")
        falta = self.__estoque.faltante(self.__modelo_cesta)
        if falta or not self.__modelo_cesta.listar_itens():
            print("[ERRO] Estoque insuficiente para montar a cesta. Falta: "
                  + (", ".join(f"{p.nome} ({q:g})" for p, q in falta.items()) or "definir o modelo da cesta"))
            return
        print("Itens da cesta (regra FEFO):")
        for produto, qtd in self.__modelo_cesta.listar_itens():
            for lote, usar in self.__estoque.previa_retirada(produto, qtd):
                print(f"  {produto.nome[:17]:<18} x{usar:<3g} lote {lote.get_id():<4} vence {lote.validade.strftime('%d/%m/%Y')}")
        if not self.__ler_entrada("Confirmar entrega? (s/n): ", "sn"):
            print("Entrega cancelada. Nada foi alterado.")
            return
        entrega = Entrega(familia, self.__modelo_cesta)
        if entrega.montar(self.__estoque):
            self.__historico.append(entrega)
            self.salvar()
            print(f"\nEntrega nº {entrega.get_id()} registrada ({entrega.total_itens():g} itens).")
            print(f"Cestas ainda possíveis: {self.__estoque.cestas_possiveis(self.__modelo_cesta)}")

    def __historico_familia(self) -> None:
        familia = self.__escolher(self.__familias, "Família")
        if not familia:
            return
        print(f"\nHistórico de {familia.descricao()} (responsável: {familia.responsavel})")
        for e in familia.historico():
            print(f"  entrega nº {e.get_id()} em {e.data.strftime('%d/%m/%Y')}: {e.total_itens():g} itens ({e.modelo.nome})")
        if not familia.historico():
            print("  Nenhuma cesta recebida ainda.")

    # ---------- 4. Doadores ----------
    def menu_doadores(self) -> None:
        while True:
            print("\n============== DOADORES ==============")
            print(f"{'Nº':>3}  {'Doador':<33}{'Documento':<16}{'Doações':>7}{'Itens':>7}")
            for d in self.__doadores:
                print(f"{d.get_id():>3}  {d.descricao()[:32]:<33}{d.documento_mascarado():<16}"
                      f"{len(d.get_doacoes()):>7}{d.total_doado():>7g}")
            print("\n1. Cadastrar doador  2. Completar cadastro  3. Contatos (doadores e famílias)  0. Voltar")
            opcao = self.__ler_entrada("Escolha uma opção: ", "escolha", list("0123"))
            if opcao == "0":
                return
            {"1": self.cadastrar_doador, "2": self.__completar_doador, "3": self.listar_contatos}[opcao]()

    def __completar_doador(self) -> None:
        doador = self.__escolher(self.__doadores, "Doador")
        if not doador:
            return
        tipo = self.__ler_entrada("Tipo (PF/PJ): ", "escolha", ["PF", "PJ"])
        documento = self.__ler_entrada("CPF (só dígitos): " if tipo == "PF" else "CNPJ (só dígitos): ",
                                       "digitos", (11,) if tipo == "PF" else (14,))
        doador.alterar_documento(tipo, documento)
        doador.telefone = self.__ler_entrada("Telefone (com DDD): ", "digitos", (10, 11))
        self.salvar()
        print(f"Cadastro atualizado: {doador.descricao()} | {doador.documento_mascarado()}")

    def listar_contatos(self) -> None:
        """Polimorfismo: doadores e famílias são tratados como Pessoa; cada um responde descricao() do seu jeito."""
        print("\n======= CONTATOS (doadores e famílias) =======")
        pessoas = self.__doadores + self.__familias
        for pessoa in pessoas:
            tel = pessoa.telefone
            tel = f"({tel[:2]}) {tel[2:-4]}-{tel[-4:]}" if tel else "sem telefone"
            print(f"  {pessoa.descricao():<35}{tel}")
        print(f"{len(pessoas)} contato(s).")

    # ---------- 5. Relatórios ----------
    def menu_relatorios(self, relatorio: Relatorio) -> None:
        while True:
            print("\n====== RELATÓRIOS E GRÁFICOS ======")
            print("1. Estoque atual\n2. Doações por período\n3. Doações por doador\n4. Entregas por família")
            print("5. Gráfico: estoque por categoria\n6. Gráfico: doações por mês\n7. Gráfico: maiores doadores\n0. Voltar")
            opcao = self.__ler_entrada("Escolha uma opção: ", "escolha", list("01234567"))
            if opcao == "0":
                return
            try:
                if opcao in "1234":
                    if opcao == "1":
                        linhas, nome = relatorio.estoque_atual(), "estoque_atual"
                    elif opcao == "2":
                        inicio = self.__ler_entrada("Início (dd/mm/aaaa): ", "data")
                        fim = self.__ler_entrada("Fim (dd/mm/aaaa): ", "data")
                        linhas, nome = relatorio.doacoes_por_periodo(inicio, fim), "doacoes_periodo"
                    elif opcao == "3":
                        linhas, nome = relatorio.doacoes_por_doador(), "doacoes_por_doador"
                    else:
                        linhas, nome = relatorio.entregas_por_familia(), "entregas_por_familia"
                    print("\n" + relatorio.formatar(linhas))
                    if self.__ler_entrada("\nExportar em CSV? (s/n): ", "sn"):
                        print(f"Arquivo salvo em {relatorio.exportar_csv(linhas, nome)}")
                else:
                    grafico = {"5": relatorio.grafico_estoque_categoria, "6": relatorio.grafico_doacoes_mes,
                               "7": relatorio.grafico_maiores_doadores}[opcao]
                    print(f"Gráfico salvo em {grafico()}")
            except (ValueError, RuntimeError) as erro:
                print(f"[AVISO] {erro}")

    # ---------- 6. Importação ----------
    def menu_importar(self) -> None:
        print("\n===== IMPORTAR PLANILHA ANTIGA (CSV) =====")
        print("Colunas: " + ", ".join(CABECALHO_CSV) + " (data_doacao opcional)")
        padrao = os.path.join("entrada", "planilha_antiga.csv")
        caminho = self.__ler_entrada(f"Caminho do arquivo [{padrao}]: ", "texto_opcional") or padrao
        if self.__historico and not self.__ler_entrada(
                "[AVISO] Já existem doações registradas. Importar a mesma planilha de novo duplica os lotes. "
                "Continuar? (s/n): ", "sn"):
            return
        self.importar_csv(caminho)
        if self.__ler_entrada("Salvar os dados agora? (s/n): ", "sn"):
            self.salvar()
            print(f"Dados salvos em {self._arquivo_dados}.")

    def importar_csv(self, caminho: str) -> int:
        """Lê a planilha antiga; linhas inválidas são ignoradas e listadas em saida/erros_importacao.txt."""
        try:
            with open(caminho, encoding="utf-8-sig") as f:
                texto = f.read()
        except UnicodeDecodeError:              # planilha salva pelo Excel no Windows
            with open(caminho, encoding="cp1252") as f:
                texto = f.read()
        separador = ";" if ";" in texto.split("\n", 1)[0] else ","
        leitor = csv.DictReader(io.StringIO(texto), delimiter=separador, restval="")
        colunas = [c.strip().lower() for c in (leitor.fieldnames or [])]
        if not set(CABECALHO_CSV) <= set(colunas):
            raise ValueError("Cabeçalho inválido. Esperado: " + ",".join(CABECALHO_CSV))
        leitor.fieldnames = colunas
        grupos: dict[tuple, Doacao] = {}        # uma doação por doador e data
        erros, total = [], 0
        for linha in leitor:
            total += 1
            try:
                nome, nome_doador, qtd, validade, data_doacao = self.__ler_linha_csv(linha)
                produto = self.__produto_por_nome(nome) or Produto(nome, linha["categoria"], linha["unidade"])
            except ValueError as erro:
                originais = separador.join(v for v in linha.values() if isinstance(v, str))
                erros.append(f"linha {leitor.line_num}: {erro} -> {originais}")
                continue
            if produto not in self.__produtos:
                self.__produtos.append(produto)
            doador = next((d for d in self.__doadores if d.nome.lower() == nome_doador.lower()), None)
            if not doador:
                # enxuto: doador da planilha entra sem tipo, documento e telefone → completar no menu Doadores
                doador = Doador(nome_doador, "", "", "")
                self.__doadores.append(doador)
            chave = (doador.get_id(), data_doacao)
            if chave not in grupos:
                grupos[chave] = Doacao(doador, data_doacao)
            grupos[chave].adicionar_item(produto, qtd, validade)
        for doacao in grupos.values():
            doacao.registrar(self.__estoque)
            self.__historico.append(doacao)
        self.__historico.sort(key=lambda m: m.data)
        os.makedirs(os.path.dirname(ARQUIVO_ERROS), exist_ok=True)
        with open(ARQUIVO_ERROS, "w", encoding="utf-8") as f:
            f.write("\n".join(erros) + ("\n" if erros else "Nenhum erro.\n"))
        importadas = total - len(erros)
        print(f"Lendo {total} linhas...\n")
        print(f"Importadas: {importadas:>4}  ({len(grupos)} {'doação' if len(grupos) == 1 else 'doações'})")
        print(f"Ignoradas:  {len(erros):>4}  (dados inválidos)")
        print(f"Detalhes em {ARQUIVO_ERROS}")
        return importadas

    def __ler_linha_csv(self, linha: dict) -> tuple:
        """Valida uma linha da planilha; erro com o motivo em português se algo estiver errado."""
        nome, nome_doador = linha["produto"].strip(), linha["doador"].strip()
        if not nome or not nome_doador:
            raise ValueError("produto ou doador vazio")
        try:
            qtd = float(linha["quantidade"].replace(",", "."))
        except ValueError:
            raise ValueError("quantidade não é número") from None
        if qtd <= 0:
            raise ValueError("quantidade deve ser maior que 0")
        try:
            validade = self.__data(linha["validade"])
            texto = linha.get("data_doacao", "").strip()
            data_doacao = self.__data(texto) if texto else date.today()
        except ValueError:
            raise ValueError("data inválida (use dd/mm/aaaa)") from None
        return nome, nome_doador, qtd, validade, data_doacao

    # ---------- persistência ----------
    def carregar(self) -> bool:
        """Lê o JSON e recria os objetos. Devolve False se não houver arquivo (primeira execução)."""
        if not os.path.exists(self._arquivo_dados):
            return False
        try:
            with open(self._arquivo_dados, encoding="utf-8") as f:
                dados = json.load(f)
            produtos = {d["id"]: Produto(d["nome"], d["categoria"], d["unidade"], d["id"]) for d in dados["produtos"]}
            lotes = {}
            for d in dados["lotes"]:
                lote = Lote(produtos[d["produto_id"]], d["quantidade_inicial"], date.fromisoformat(d["validade"]),
                            date.fromisoformat(d["data_entrada"]), d["id"])
                lote.retirar(d["quantidade_inicial"] - d["quantidade"])
                lotes[lote.get_id()] = lote
            doadores = {d["id"]: Doador(d["nome"], d["telefone"], d["tipo"], d["documento"], d["id"])
                        for d in dados["doadores"]}
            familias = {d["id"]: Familia(d["nome"], d["telefone"], d["responsavel"], d["num_pessoas"],
                                         d["endereco"], d["id"]) for d in dados["familias"]}
            modelo = ModeloCesta(dados["modelo_cesta"]["nome"])
            for item in dados["modelo_cesta"]["itens"]:
                modelo.adicionar_item(produtos[item["produto_id"]], item["quantidade"])
            historico: list[Doacao | Entrega] = []
            for d in dados["doacoes"]:
                doacao = Doacao(doadores[d["doador_id"]], date.fromisoformat(d["data"]), d["id"])
                for lote_id in d["lotes"]:
                    doacao.adicionar_lote(lotes[lote_id])
                doacao.doador.registrar_doacao(doacao)
                historico.append(doacao)
            for d in dados["entregas"]:
                itens = [(produtos[i["produto_id"]], i["quantidade"]) for i in d["itens"]]
                entrega = Entrega(familias[d["familia_id"]], modelo, date.fromisoformat(d["data"]), d["id"], itens)
                entrega.familia.registrar_entrega(entrega)
                historico.append(entrega)
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as erro:
            # não sobrescreve o arquivo com problema: guarda uma cópia e começa do zero
            copia = self._arquivo_dados + ".corrompido"
            os.replace(self._arquivo_dados, copia)
            print(f"[ERRO] Não foi possível ler {self._arquivo_dados} ({erro}). Cópia guardada em {copia}.")
            return False
        self.__produtos = list(produtos.values())
        for lote in lotes.values():
            self.__estoque.adicionar_lote(lote)
        self.__doadores = list(doadores.values())
        self.__familias = list(familias.values())
        self.__modelo_cesta = modelo
        self.__historico = sorted(historico, key=lambda m: m.data)
        return True

    def salvar(self) -> None:
        dados = {
            "produtos": [p.to_dict() for p in self.__produtos],
            "lotes": self.__estoque.to_dict(),
            "doadores": [d.to_dict() for d in self.__doadores],
            "familias": [f.to_dict() for f in self.__familias],
            "doacoes": [m.to_dict() for m in self.__historico if isinstance(m, Doacao)],
            "entregas": [m.to_dict() for m in self.__historico if isinstance(m, Entrega)],
            "modelo_cesta": self.__modelo_cesta.to_dict(),
        }
        pasta = os.path.dirname(self._arquivo_dados)
        if pasta:
            os.makedirs(pasta, exist_ok=True)
        temporario = self._arquivo_dados + ".tmp"   # grava em outro arquivo e troca: não corrompe se o programa cair
        with open(temporario, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        os.replace(temporario, self._arquivo_dados)

    # ---------- apoio interno ----------
    @staticmethod
    def __data(texto: str) -> date:
        """Converte dd/mm/aaaa; recusa ano com 2 dígitos ("10/10/26" viraria o ano 26)."""
        data = datetime.strptime(texto.strip(), "%d/%m/%Y").date()
        if data.year < 2000:
            raise ValueError("ano inválido")
        return data

    def __produto_por_nome(self, nome: str) -> Produto | None:
        return next((p for p in self.__produtos if p.nome.lower() == nome.strip().lower()), None)

    def __criar_padrao(self) -> None:
        """Primeira execução: catálogo básico e a cesta padrão."""
        catalogo = [("Arroz 5 kg", "grãos", 1), ("Feijão 1 kg", "grãos", 2), ("Óleo 900 ml", "óleos", 1),
                    ("Macarrão 500 g", "massas", 2), ("Leite 1 L", "laticínios", 2),
                    ("Sardinha 125 g", "enlatados", 2), ("Sabonete", "higiene", 2)]
        for nome, categoria, qtd in catalogo:
            produto = Produto(nome, categoria, "un")
            self.__produtos.append(produto)
            self.__modelo_cesta.adicionar_item(produto, qtd)
