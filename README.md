# combustiveis-pt

[![CI](https://github.com/JoseFerrao20/combustiveis-pt/actions/workflows/ci.yml/badge.svg)](https://github.com/JoseFerrao20/combustiveis-pt/actions/workflows/ci.yml)
[![Licença: MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-blue)](LICENSE)

**Quanto do que pagas por um litro de gasolina é imposto?** Um pipeline de dados com os preços semanais dos combustíveis em Portugal e nos outros países da UE desde 2005, a partir do [Weekly Oil Bulletin](https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en) da Comissão Europeia.

Na semana de 19/10/2026, um litro de gasolina 95 custava 2,099 € em Portugal:

| | € por litro |
|---|---|
| Produto (antes de impostos) | 1,122 |
| ISP (imposto sobre os produtos petrolíferos) | 0,426 |
| Outros impostos (contribuição de serviço rodoviário, carbono) | 0,159 |
| IVA (23 %) | 0,392 |
| **Preço** | **2,099** |

Quase **47 %** do preço são impostos. A decomposição bate certo com o preço publicado ao cêntimo, e essa verificação faz parte dos testes.

## Perguntas

- Quanto do preço é imposto, e como mudou desde 2005?
- Portugal comparado com Espanha e com a média da UE e da zona euro.
- O efeito das mudanças do ISP (por exemplo, as descidas de 2022).

## Arquitetura

```mermaid
flowchart LR
  WOB["Weekly Oil Bulletin<br/>(Comissão Europeia, .xlsx)"] --> I["ingest<br/>Python"]
  I --> L[("landing<br/>Parquet + manifesto")]
  L --> D["dbt + DuckDB<br/>staging · marts · testes"]
  D --> E["Evidence<br/>site estático"]
```

| Fase | Estado |
|---|---|
| **Ingestão**: descarrega o histórico, passa as folhas "largas" (uma coluna por país) a tabelas "longas" e escreve Parquet, com um manifesto (origem, data, SHA-256) | ✅ |
| **Transformação**: modelos dbt em DuckDB (staging, imposto em vigor em cada semana com `ASOF JOIN`, decomposição do preço), testes de dados e testes unitários do dbt | ✅ |
| **Painel**: site estático com Evidence no GitHub Pages, atualizado todas as semanas pelo GitHub Actions | a seguir |

A escolha da fonte está em [`docs/adr/0001-fonte-weekly-oil-bulletin.md`](docs/adr/0001-fonte-weekly-oil-bulletin.md).

## Correr

Com o [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run combustiveis ingest                         # descarrega e escreve data/landing/
uv run combustiveis ingest --ficheiro historico.xlsx   # a partir de um ficheiro já descarregado
```

A camada landing fica em `data/landing/`: `prices.parquet` (semana, país, produto, com ou sem impostos, valor por 1000 L), `taxes.parquet` (IVA, ISP e outros impostos, com a data de entrada em vigor) e `manifest.json`.

Depois, a transformação com o dbt (escreve `data/warehouse.duckdb`):

```bash
uv sync --all-groups
uv run dbt build --project-dir transform --profiles-dir transform
```

O resultado é a tabela `fct_fuel_prices`, uma linha por semana, país e produto:

| Coluna | O que é |
|---|---|
| `price_with_tax`, `price_without_tax` | preços publicados, em € por 1000 L (por tonelada nos fuelóleos) |
| `vat_rate`, `vat_amount` | taxa de IVA em vigor nessa semana e o IVA incluído no preço |
| `excise_and_other_taxes` | ISP e outros impostos: o resto da diferença entre os dois preços |
| `taxes_total`, `tax_share` | todos os impostos e a parte do preço que representam |
| `reported_excise`, `reported_other_taxes`, `tax_tables_gap` | o ISP e os outros impostos das tabelas do boletim, e quanto ficam longe do valor acima (só a partir da entrada no euro, porque as tabelas estão na moeda nacional) |

A decomposição soma sempre o preço; quando as tabelas de impostos do boletim não a explicam, a diferença fica à vista em `tax_tables_gap`, em vez de escondida.

## Desenvolvimento

```bash
uv run pytest                                      # testes, cobertura ≥ 90 %
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Os testes usam uma amostra do ficheiro real (`tests/fixtures/oil_bulletin_sample.xlsx`, gerada com `scripts/make_sample.py`), com o mesmo formato: se a Comissão mudar o ficheiro, é aí que se vê. O CI corre também o `dbt build` com essa amostra.

No dbt (`transform/`):

- **testes de dados**: chaves únicas e não nulas, valores aceites, relações com os países e produtos (seeds), e o preço com impostos nunca abaixo do preço sem impostos;
- **testes unitários** do dbt sobre a decomposição, com valores escritos à mão (incluindo o preço português de 19/10/2026);
- **erros conhecidos da fonte** no seed `known_source_errors`, cada um com a explicação: os testes ignoram essas semanas, e um erro novo faz falhar o build;
- **um aviso** (não falha) quando as tabelas de ISP e de outros impostos não explicam o preço português.

## Fonte e licença

Dados: © União Europeia, [Weekly Oil Bulletin](https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en), reprodução autorizada com indicação da fonte. Os preços são médias nacionais ponderadas, não os de um posto.

Código: [MIT](LICENSE).
