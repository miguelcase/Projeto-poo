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

Os dados ficam em `dados/cesta_viva.json` (salvos ao sair e depois de cada doação ou entrega).
Relatórios em CSV e gráficos em PNG vão para a pasta `saida/`.

## Testes

```bash
python -m unittest discover -s tests -v
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

A pasta `docs/` tem os PDFs entregues em cada etapa: proposta (Etapa 1), diagramas de classes e telas (Etapa 2) e a
documentação completa com prints, testes, limitações e o que falta (Etapa 3).

## Formato da planilha antiga (CSV)

Cabeçalho obrigatório (separador vírgula ou ponto e vírgula; `data_doacao` é opcional):

```
produto,categoria,unidade,quantidade,validade,doador,data_doacao
Arroz 5 kg,grãos,un,40,15/03/2027,Mercado Bom Preço,12/05/2026
```

Linhas com erro são ignoradas e listadas em `saida/erros_importacao.txt`.

## Privacidade

O JSON guarda CPF/CNPJ e telefones. Por isso `dados/*.json` está no `.gitignore`: não suba dados reais para o GitHub.
