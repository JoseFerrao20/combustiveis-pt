{{ config(
    materialized='external',
    location=env_var('TRACKED_COMPETITORS_EXPORT_PATH', 'data/tracked_station_competitors.parquet'),
) }}
-- Os concorrentes a 5 km de cada posto acompanhado na última fotografia, com o preço de cada
-- combustível do painel, para a tabela da página "Postos acompanhados".
select
    neighbours.snapshot_date,
    neighbours.station_id,
    tracked.label,
    neighbours.competitor_id,
    prices.station_name,
    prices.brand,
    prices.brand_segment,
    prices.station_type,
    prices.latitude,
    prices.longitude,
    neighbours.distance_km,
    prices.fuel,
    fuels.name as fuel_name,
    prices.price,
    prices.updated_at,
    prices.is_current
from {{ ref('int_tracked_station_neighbours') }} as neighbours
inner join {{ ref('tracked_stations') }} as tracked using (station_id)
inner join {{ ref('fct_station_prices') }} as prices
    on prices.snapshot_date = neighbours.snapshot_date
    and prices.station_id = neighbours.competitor_id
inner join {{ ref('dgeg_fuels') }} as fuels using (fuel)
where fuels.in_dashboard
    and neighbours.snapshot_date = (select max(snapshot_date) from {{ ref('fct_station_prices') }})
