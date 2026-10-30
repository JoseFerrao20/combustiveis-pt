-- A mudança dos preços dos postos à segunda-feira, segundo as fotografias diárias da DGEG: para
-- cada segunda com fotografia, a média da mudança de cada posto entre a fotografia anterior
-- (até 3 dias antes) e a de segunda, só com os postos que têm o preço atualizado nos dois dias.
-- Serve para comparar a previsão logo na segunda-feira, sem esperar pelo boletim europeu.
with

prices as (
    select prices.snapshot_date, prices.station_id, fuels.wob_product as product, prices.price
    from {{ ref('fct_station_prices') }} as prices
    inner join {{ ref('dgeg_fuels') }} as fuels using (fuel)
    where prices.is_current and fuels.wob_product in ('euro95', 'diesel')
),

snapshots as (select distinct snapshot_date from prices),

mondays as (
    select
        monday.snapshot_date as target_week,
        max(previous.snapshot_date) as previous_snapshot_date
    from snapshots as monday
    inner join snapshots as previous
        on previous.snapshot_date < monday.snapshot_date
        and previous.snapshot_date >= monday.snapshot_date - interval 3 day
    where dayofweek(monday.snapshot_date) = 1
    group by all
)

select
    mondays.target_week,
    now.product,
    mondays.previous_snapshot_date,
    avg(now.price - before.price) as dgeg_change,
    count(*) as dgeg_stations,
    avg(case when now.price <> before.price then 1.0 else 0.0 end) as dgeg_share_changed
from mondays
inner join prices as now on now.snapshot_date = mondays.target_week
inner join prices as before
    on before.snapshot_date = mondays.previous_snapshot_date
    and before.station_id = now.station_id
    and before.product = now.product
group by all
