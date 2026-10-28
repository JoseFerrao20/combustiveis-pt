{{ config(
    materialized='external',
    location=env_var('STATIONS_EXPORT_PATH', 'data/stations_latest.parquet'),
) }}
-- A última fotografia da DGEG, para o mapa e as tabelas do painel (dashboard/pages/postos.md):
-- um posto por linha e combustível, só nos combustíveis do painel.
select
    prices.snapshot_date,
    prices.station_id,
    prices.station_name,
    prices.brand,
    prices.brand_segment,
    prices.station_type,
    prices.district,
    prices.municipality,
    prices.locality,
    prices.latitude,
    prices.longitude,
    prices.fuel,
    fuels.name as fuel_name,
    prices.price,
    prices.updated_at,
    prices.is_current,
    neighbours.competitors_2km,
    neighbours.competitors_5km,
    neighbours.nearest_competitor_km
from {{ ref('fct_station_prices') }} as prices
inner join {{ ref('dgeg_fuels') }} as fuels using (fuel)
left join {{ ref('int_station_neighbours') }} as neighbours using (snapshot_date, station_id)
where fuels.in_dashboard
    and prices.snapshot_date = (select max(snapshot_date) from {{ ref('fct_station_prices') }})
