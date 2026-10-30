{{ config(
    materialized='external',
    location=env_var('EXPORT_PATH', 'data/road_fuel_prices.parquet'),
) }}
-- Combustíveis rodoviários em euros por litro, para o painel (dashboard/). Fica em Parquet
-- porque o Evidence traz um DuckDB mais antigo, que não abre a base de dados do dbt.
--
-- O Evidence descarrega cada fonte inteira em todas as páginas (também na dos postos, que não a
-- usa). Por isso, só vai o histórico que as páginas mostram: todas as semanas de Portugal,
-- Espanha e da média da UE, e a última semana dos outros países (a comparação da página
-- "Portugal e a Europa"). Os valores vão arredondados ao décimo de milésimo de euro.
with latest as (
    select product, max(week) as week
    from {{ ref('fct_fuel_prices') }}
    group by all
)

select
    fuel.week,
    fuel.country_code,
    countries.name as country,
    countries.kind = 'aggregate' as is_average,
    fuel.product,
    products.name as fuel,
    round(fuel.price_with_tax / 1000, 4) as price,
    round(fuel.price_without_tax / 1000, 4) as price_without_tax,
    round(fuel.excise_and_other_taxes / 1000, 4) as excise_and_other_taxes,
    round(fuel.vat_amount / 1000, 4) as vat_amount,
    round(fuel.taxes_total / 1000, 4) as taxes_total,
    fuel.vat_rate,
    round(fuel.tax_share, 4) as tax_share
from {{ ref('fct_fuel_prices') }} as fuel
inner join {{ ref('countries') }} as countries using (country_code)
inner join {{ ref('products') }} as products using (product)
inner join latest on latest.product = fuel.product
-- Só as semanas com os dois preços (falta um em casos raros, como Espanha a 8/4/2013).
where products.is_road_fuel
    and fuel.price_with_tax is not null
    and fuel.price_without_tax is not null
    and (fuel.country_code in ('PT', 'ES', 'EU') or fuel.week = latest.week)
