{{ config(severity='warn') }}
-- Aviso: a média dos postos da DGEG afasta-se mais de 5 % do preço português do Weekly Oil
-- Bulletin na mesma semana. As duas fontes não medem o mesmo (a DGEG é uma média simples dos
-- postos, o boletim uma média ponderada pelas vendas), mas não deviam andar longe.
with

dgeg as (
    select
        date_trunc('week', prices.snapshot_date) as week,
        fuels.wob_product as product,
        avg(prices.price) as dgeg_price
    from {{ ref('fct_station_prices') }} as prices
    inner join {{ ref('dgeg_fuels') }} as fuels using (fuel)
    where prices.is_current and fuels.wob_product is not null
    group by all
),

bulletin as (
    select week, product, price_with_tax / 1000 as bulletin_price
    from {{ ref('fct_fuel_prices') }}
    where country_code = 'PT'
)

select dgeg.*, bulletin.bulletin_price
from dgeg
inner join bulletin using (week, product)
where abs(dgeg.dgeg_price / bulletin.bulletin_price - 1) > 0.05
