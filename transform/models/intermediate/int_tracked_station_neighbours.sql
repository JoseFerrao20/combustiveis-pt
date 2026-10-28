-- Os concorrentes a 5 km de cada posto acompanhado (seed tracked_stations), em cada dia de
-- fotografia, com a distância em linha reta (a mesma fórmula de int_station_neighbours).
with

tracked as (select * from {{ ref('tracked_stations') }}),

stations as (
    select distinct snapshot_date, station_id, latitude, longitude
    from {{ ref('stg_dgeg__station_prices') }}
    where latitude is not null and longitude is not null
),

pairs as (
    select
        a.snapshot_date,
        a.station_id,
        b.station_id as competitor_id,
        2 * 6371 * asin(sqrt(
            pow(sin(radians(b.latitude - a.latitude) / 2), 2)
            + cos(radians(a.latitude)) * cos(radians(b.latitude))
            * pow(sin(radians(b.longitude - a.longitude) / 2), 2)
        )) as distance_km
    from stations as a
    inner join tracked on tracked.station_id = a.station_id
    inner join stations as b
        on b.snapshot_date = a.snapshot_date
        and b.station_id <> a.station_id
        and abs(b.latitude - a.latitude) < 0.1
        and abs(b.longitude - a.longitude) < 0.13
)

select * from pairs where distance_km <= 5
