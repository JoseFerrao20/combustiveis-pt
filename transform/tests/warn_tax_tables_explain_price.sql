{{ config(severity='warn') }}
-- Aviso (não erro): semanas em que as tabelas de ISP e de outros impostos do boletim não
-- explicam a parte do preço que é ISP e outros impostos (diferença acima de 1 € por 1000 L,
-- um décimo de cêntimo por litro), em Portugal e nos dois países já investigados (Lituânia e
-- Países Baixos), fora dos períodos com explicação (seed known_tax_table_issues). É um problema
-- da fonte, não do pipeline: há períodos com valores em falta, trocados ou desatualizados.
select country_code, week, product, tax_tables_gap
from {{ ref('fct_fuel_prices') }}
where country_code in ('PT', 'LT', 'NL')
    and product in ('euro95', 'diesel')
    and abs(tax_tables_gap) > 1
    and tax_tables_issue is null
