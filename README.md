# Cesta Viva

Controle de doações e estoque para bancos de alimentos comunitários.
Projeto da disciplina, grupo **Trio Ternário** (Miguel Pires, Arthur Sacomorri e João Zamora).

## Como executar

Requisitos: Python 3.12 ou mais novo.

```bash
git clone https://github.com/miguelcase/Projeto-poo.git
cd Projeto-poo
pip install -r requirements.txt    # só o Matplotlib, usado nos gráficos
python main.py
```

Na primeira execução o sistema já cria o catálogo básico e a **Cesta Padrão**. Para carregar os dados de exemplo,
use a opção **6 (Importar planilha antiga)** e aperte Enter para usar `entrada/planilha_antiga.csv`.

Os dados ficam em `dados/cesta_viva.json` (salvos ao sair e depois de cada doação, entrega, cadastro ou estorno).
Relatórios em CSV e gráficos em PNG vão para a pasta `saida/`.

## O que o sistema faz

| Menu | Funções |
|---|---|
| 1 · Estoque | saldo por produto, alertas de vencidos e de quem vence em 15 dias, cestas possíveis e o que falta; ver lotes; produtos (cadastrar, editar, remover, renomear categoria); modelo da cesta; descartar vencidos |
| 2 · Registrar doação | doador existente ou novo, um lote por item com validade, comprovante com o saldo novo |
| 3 · Famílias | cadastrar, editar, remover, entregar cesta (baixa FEFO, aviso se recebeu há menos de 30 dias), histórico, **estornar entrega** |
| 4 · Doadores | cadastrar, editar / completar cadastro, remover, contatos (doadores e famílias), **estornar doação** |
| 5 · Relatórios | estoque, doações por período, doações por doador, entregas por família (tela e CSV); 3 gráficos em PNG |
| 6 · Importar | planilha antiga em CSV; linhas com erro vão para `saida/erros_importacao.txt` |

Estorno é para lançamento feito por engano: a entrega devolve cada item ao lote de onde saiu; a doação só pode ser
estornada se nenhum item dela já saiu em cesta ou foi descartado. Família, doador ou produto com histórico não pode
ser removido.

## Testes

```bash
python -m unittest discover -s tests -v    # 26 testes
```

## Estrutura

| Arquivo | Classes | Responsável |
|---|---|---|
| `estoque.py` | Produto, Lote, Estoque, ModeloCesta | Miguel Pires |
| `pessoas.py` | Pessoa (abstrata), Doador, Familia | Arthur Sacomorri |
| `movimentacoes.py` | Doacao, Entrega | Arthur Sacomorri |
| `sistema.py` | Sistema (menu, JSON, importação CSV) | João Zamora |
| `relatorio.py` | Relatorio (relatórios e gráficos) | João Zamora |
| `main.py` | programa principal | todos |

## Documentação

A pasta `docs/` tem os PDFs entregues em cada etapa: proposta (Etapa 1), diagramas de classes e telas (Etapa 2),
documentação da Etapa 3 e a **documentação final** (`Entrega_Final_Cesta_Viva.pdf`), com os diagramas finais, as telas
reais, os testes e o roteiro da demonstração.

Os diagramas finais também estão em `docs/` em formato editável do draw.io (`diagrama_classes_final.drawio` e
`diagrama_casos_de_uso.drawio`) e em PNG. Para editar: abra o arquivo em [app.diagrams.net](https://app.diagrams.net).

## Formato da planilha antiga (CSV)

Cabeçalho obrigatório (separador vírgula ou ponto e vírgula; `data_doacao` é opcional):

```
produto,categoria,unidade,quantidade,validade,doador,data_doacao
Arroz 5 kg,grãos,un,40,15/03/2027,Mercado Bom Preço,12/05/2026
```

Linhas com erro são ignoradas e listadas em `saida/erros_importacao.txt`.

## Privacidade

O JSON guarda CPF/CNPJ e telefones. Por isso `dados/*.json` está no `.gitignore`: não suba dados reais para o GitHub.
