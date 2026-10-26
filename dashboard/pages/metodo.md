---
title: Como se calcula
---

## Os dados

O [Weekly Oil Bulletin](https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en) publica, todas as semanas e para cada país da UE, o preço médio de venda ao público de cada combustível, com e sem impostos, e as tabelas de IVA, ISP e outros impostos. O código está em [JoseFerrao20/combustiveis-pt](https://github.com/JoseFerrao20/combustiveis-pt): ingestão em Python para Parquet, transformação com o dbt e o DuckDB, e este painel com o Evidence.

## A divisão do preço

Para cada semana, país e combustível:

- **IVA** = preço − preço ÷ (1 + taxa de IVA em vigor nessa semana);
- **ISP e outros impostos** = preço ÷ (1 + taxa de IVA) − preço sem impostos;
- **produto** = preço sem impostos (petróleo, refinação, distribuição e margens).

As três partes somam sempre o preço publicado. As tabelas de ISP e de outros impostos do boletim servem só para verificar a conta.

## Limitações

- Em Portugal, as tabelas de ISP e de outros impostos do boletim batem certo com o preço ao cêntimo em muitos anos, mas não em 2008–2011, 2016–2018 e 2025: aí faltam valores, ou estão trocados entre as duas tabelas. A divisão acima não depende dessas tabelas, por isso não é afetada.
- Há erros de uma semana no próprio boletim (por exemplo, nos fuelóleos da Irlanda e da Bélgica). Estão listados no projeto, com a explicação, e os testes de dados ignoram essas semanas.
- As médias da UE e da zona euro são ponderadas pelo consumo de cada país.

```sql semanas
select count(distinct week) as semanas, min(week) as desde, max(week) as ate
from combustiveis.precos
```

O painel tem <Value data={semanas} column=semanas /> semanas de dados, de <Value data={semanas} column=desde fmt="dd/mm/yyyy" /> a <Value data={semanas} column=ate fmt="dd/mm/yyyy" />.

Dados: © União Europeia, reprodução autorizada com indicação da fonte.

