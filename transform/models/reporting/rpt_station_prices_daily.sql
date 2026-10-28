{{ config(
    materialized='external',
    location=env_var('STATIONS_DAILY_EXPORT_PATH', 'data/station_prices_daily.parquet'),
) }}
-- Preço médio por dia e combustível, no país, por grupo de marcas, por marca e por distrito,
-- para os gráficos do painel. Só os preços atualizados nos últimos 30 dias (is_current).
with

prices as (
    select prices.*, fuels.name as fuel_name
    from {{ ref('fct_station_prices') }} as prices
    inner join {{ ref('dgeg_fuels') }} as fuels using (fuel)
    where fuels.in_dashboard and prices.is_current
),

grouped as (
    select snapshot_date, fuel, fuel_name, 'Portugal' as dimension, 'Portugal' as label, price
    from prices
    union all
    select snapshot_date, fuel, fuel_name, 'Grupo de marcas', brand_segment, price from prices
    union all
    select snapshot_date, fuel, fuel_name, 'Marca', brand, price from prices
    union all
    select snapshot_date, fuel, fuel_name, 'Distrito', district, price from prices
)

select
    snapshot_date,
    fuel,
    fuel_name,
    dimension,
    label,
    count(*) as stations,
    avg(price) as avg_price,
    median(price) as median_price,
    min(price) as min_price,
    max(price) as max_price
from grouped
group by all
