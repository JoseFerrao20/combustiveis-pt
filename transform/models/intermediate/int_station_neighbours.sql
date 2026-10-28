{{ config(materialized='table') }}
-- Quantos postos concorrentes há perto de cada posto, em cada dia de fotografia: a 2 km e a
-- 5 km em linha reta (fórmula de haversine, raio da Terra de 6371 km), e a distância ao mais
-- próximo. Sem a extensão espacial do DuckDB, para o CI não depender de a descarregar.
with

stations as (
    select distinct snapshot_date, station_id, latitude, longitude
    from {{ ref('stg_dgeg__station_prices') }}
    where latitude is not null and longitude is not null
),

pairs as (
    select
        a.snapshot_date,
        a.station_id,
        b.station_id as other_id,
        2 * 6371 * asin(sqrt(
            pow(sin(radians(b.latitude - a.latitude) / 2), 2)
            + cos(radians(a.latitude)) * cos(radians(b.latitude))
            * pow(sin(radians(b.longitude - a.longitude) / 2), 2)
        )) as distance_km
    from stations as a
    inner join stations as b
        on b.snapshot_date = a.snapshot_date
        and b.station_id <> a.station_id
        -- Só os vizinhos dentro de um quadrado de uns 11 km de lado, antes de calcular a
        -- distância (0,1° de latitude são 11 km; 0,13° de longitude, a 40° N, são 11 km).
        and abs(b.latitude - a.latitude) < 0.1
        and abs(b.longitude - a.longitude) < 0.13
)

select
    stations.snapshot_date,
    stations.station_id,
    count(pairs.other_id) filter (where pairs.distance_km <= 2) as competitors_2km,
    count(pairs.other_id) filter (where pairs.distance_km <= 5) as competitors_5km,
    min(pairs.distance_km) as nearest_competitor_km
from stations
left join pairs using (snapshot_date, station_id)
group by all
