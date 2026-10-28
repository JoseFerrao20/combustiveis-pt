{{ config(
    materialized='external',
    location=env_var('TRACKED_DAILY_EXPORT_PATH', 'data/tracked_stations_daily.parquet'),
) }}
-- Cada posto acompanhado (seed tracked_stations), por dia e combustível do painel: o preço, a
-- média dos concorrentes a 5 km e do concelho, e a posição entre os postos a 5 km (1 = o mais
-- barato). As médias e a posição usam só os preços atualizados nos últimos 30 dias.
with

tracked as (select * from {{ ref('tracked_stations') }}),

prices as (
    select prices.*, fuels.name as fuel_name
    from {{ ref('fct_station_prices') }} as prices
    inner join {{ ref('dgeg_fuels') }} as fuels using (fuel)
    where fuels.in_dashboard
),

own as (
    select prices.*, tracked.label, tracked.location
    from prices
    inner join tracked using (station_id)
),

competitors as (
    select
        neighbours.snapshot_date,
        neighbours.station_id,
        prices.fuel,
        count(*) as competitors,
        avg(prices.price) as competitors_avg_price,
        min(prices.price) as competitors_min_price
    from {{ ref('int_tracked_station_neighbours') }} as neighbours
    inner join prices
        on prices.snapshot_date = neighbours.snapshot_date
        and prices.station_id = neighbours.competitor_id
    where prices.is_current
    group by all
),

cheaper as (
    select
        neighbours.snapshot_date,
        neighbours.station_id,
        own.fuel,
        count(*) filter (where prices.price < own.price) as cheaper_competitors
    from {{ ref('int_tracked_station_neighbours') }} as neighbours
    inner join own using (snapshot_date, station_id)
    inner join prices
        on prices.snapshot_date = neighbours.snapshot_date
        and prices.station_id = neighbours.competitor_id
        and prices.fuel = own.fuel
    where prices.is_current
    group by all
),

municipality as (
    select snapshot_date, municipality, fuel, avg(price) as municipality_avg_price
    from prices
    where is_current
    group by all
)

select
    own.snapshot_date,
    own.station_id,
    own.label,
    own.location,
    own.station_name,
    own.brand,
    own.municipality,
    own.latitude,
    own.longitude,
    own.fuel,
    own.fuel_name,
    own.price,
    own.updated_at,
    own.is_current,
    competitors.competitors,
    competitors.competitors_avg_price,
    competitors.competitors_min_price,
    coalesce(cheaper.cheaper_competitors, 0) + 1 as rank_5km,
    municipality.municipality_avg_price
from own
left join competitors using (snapshot_date, station_id, fuel)
left join cheaper using (snapshot_date, station_id, fuel)
left join municipality using (snapshot_date, municipality, fuel)
