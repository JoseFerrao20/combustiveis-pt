{{ config(
    materialized='external',
    location=env_var('EXPORT_PATH', 'data/road_fuel_prices.parquet'),
) }}
-- Combustíveis rodoviários em euros por litro, para o painel (dashboard/). Fica em Parquet
-- porque o Evidence traz um DuckDB mais antigo, que não abre a base de dados do dbt.
select
    fuel.week,
    fuel.country_code,
    countries.name as country,
    countries.kind = 'aggregate' as is_average,
    fuel.product,
    products.name as fuel,
    fuel.price_with_tax / 1000 as price,
    fuel.price_without_tax / 1000 as price_without_tax,
    fuel.excise_and_other_taxes / 1000 as excise_and_other_taxes,
    fuel.vat_amount / 1000 as vat_amount,
    fuel.taxes_total / 1000 as taxes_total,
    fuel.vat_rate,
    fuel.tax_share
from {{ ref('fct_fuel_prices') }} as fuel
inner join {{ ref('countries') }} as countries using (country_code)
inner join {{ ref('products') }} as products using (product)
-- Só as semanas com os dois preços (falta um em casos raros, como Espanha a 8/4/2013).
where products.is_road_fuel
    and fuel.price_with_tax is not null
    and fuel.price_without_tax is not null
