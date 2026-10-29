-- A evolução do preço de cada posto e combustível entre fotografias: o preço da fotografia
-- anterior, o de há uma semana (a última fotografia com pelo menos 7 dias), o dia da última
-- mudança e os preços dos últimos 7 dias como texto, para o painel. Antes de haver histórico,
-- as colunas ficam vazias.
with

prices as (
    select snapshot_date, station_id, fuel, price
    from {{ ref('fct_station_prices') }}
),

with_previous as (
    select
        *,
        lag(price) over station_fuel as previous_price,
        lag(snapshot_date) over station_fuel as previous_snapshot_date
    from prices
    window station_fuel as (partition by station_id, fuel order by snapshot_date)
),

changes as (
    -- Os dias em que o preço mudou em relação à fotografia anterior.
    select station_id, fuel, max(snapshot_date) as last_change_date
    from with_previous
    where previous_price is not null and price <> previous_price
    group by all
),

latest as (
    select * from with_previous
    where snapshot_date = (select max(snapshot_date) from prices)
),

week_ago as (
    select latest.station_id, latest.fuel, arg_max(prices.price, prices.snapshot_date) as price_7d
    from latest
    inner join prices
        on prices.station_id = latest.station_id
        and prices.fuel = latest.fuel
        and prices.snapshot_date <= latest.snapshot_date - interval 7 day
    group by all
),

recent as (
    -- "29/10: 1,919 · 28/10: 1,929": os últimos 7 dias, do mais recente para o mais antigo.
    select
        prices.station_id,
        prices.fuel,
        string_agg(
            strftime(prices.snapshot_date, '%d/%m') || ': '
                || replace(printf('%.3f', prices.price), '.', ','),
            ' · ' order by prices.snapshot_date desc
        ) as history_7d
    from prices
    where prices.snapshot_date > (select max(snapshot_date) from prices) - interval 7 day
    group by all
)

select
    latest.snapshot_date,
    latest.station_id,
    latest.fuel,
    latest.previous_price,
    latest.previous_snapshot_date,
    round(latest.price - latest.previous_price, 3) as change_since_previous,
    week_ago.price_7d,
    changes.last_change_date,
    recent.history_7d
from latest
left join week_ago using (station_id, fuel)
left join changes using (station_id, fuel)
left join recent using (station_id, fuel)
