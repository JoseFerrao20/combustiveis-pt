{{ config(
    materialized='external',
    location=env_var('ISLANDS_EXPORT_PATH', 'data/island_prices.parquet'),
) }}
-- Os preços máximos dos Açores e da Madeira, com o período em que estiveram em vigor e, para
-- comparar, o preço médio dos postos do continente (DGEG) na última fotografia desse período.
-- No continente não há preço máximo: é o preço médio a que se vende.
with

max_prices as (
    select
        *,
        lead(valid_from) over (partition by region, fuel order by valid_from) - 1 as valid_to
    from {{ ref('stg_ilhas__max_prices') }}
),

continent as (
    select snapshot_date, fuel, avg(price) as avg_price, count(*) as stations
    from {{ ref('fct_station_prices') }}
    where is_current and fuel in ('gasolina_95', 'gasoleo')
    group by all
),

matched as (
    select
        max_prices.region,
        max_prices.fuel,
        max_prices.valid_from,
        max(continent.snapshot_date) as continent_snapshot
    from max_prices
    inner join continent
        on continent.fuel = max_prices.fuel
        and continent.snapshot_date >= max_prices.valid_from
        and continent.snapshot_date <= coalesce(max_prices.valid_to, current_date)
    group by all
)

select
    max_prices.region,
    case max_prices.region when 'acores' then 'Açores' else 'Madeira' end as region_name,
    max_prices.fuel,
    case max_prices.fuel when 'gasolina_95' then 'Gasolina 95' else 'Gasóleo' end as fuel_name,
    max_prices.valid_from,
    max_prices.valid_to,
    max_prices.price,
    max_prices.act,
    max_prices.published,
    max_prices.source_url,
    matched.continent_snapshot,
    continent.avg_price as continent_avg_price,
    continent.stations as continent_stations
from max_prices
left join matched using (region, fuel, valid_from)
left join continent
    on continent.fuel = max_prices.fuel and continent.snapshot_date = matched.continent_snapshot
order by region, fuel, valid_from
