{{ config(severity='warn') }}
-- Aviso (não erro): semanas em que as tabelas de ISP e de outros impostos do boletim não
-- explicam a parte do preço português que é ISP e outros impostos (diferença acima de 1 € por
-- 1000 L, um décimo de cêntimo por litro). É um problema da fonte, não do pipeline: há
-- períodos com valores em falta ou trocados entre as duas tabelas.
select week, product, tax_tables_gap
from {{ ref('fct_fuel_prices') }}
where country_code = 'PT'
    and product in ('euro95', 'diesel')
    and abs(tax_tables_gap) > 1
