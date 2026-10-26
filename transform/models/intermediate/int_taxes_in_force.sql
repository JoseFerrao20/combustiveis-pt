-- Os impostos em vigor em cada semana: o último valor com valid_from até essa semana.
-- O ISP português muda quase todas as semanas desde 2022, em datas que não são segundas-feiras,
-- por isso um ASOF JOIN e não uma junção pela data.
with

prices as (
    select week, country_code, product from {{ ref('int_prices_pivoted') }}
),

vat as (select * from {{ ref('stg_bulletin__taxes') }} where tax = 'vat'),
excise as (select * from {{ ref('stg_bulletin__taxes') }} where tax = 'excise'),
other as (select * from {{ ref('stg_bulletin__taxes') }} where tax = 'other')

select
    prices.week,
    prices.country_code,
    prices.product,
    vat.value as vat_rate,
    excise.value as excise,
    other.value as other_taxes
from prices
asof left join vat
    on vat.country_code = prices.country_code
    and vat.product = prices.product
    and prices.week >= vat.valid_from
asof left join excise
    on excise.country_code = prices.country_code
    and excise.product = prices.product
    and prices.week >= excise.valid_from
asof left join other
    on other.country_code = prices.country_code
    and other.product = prices.product
    and prices.week >= other.valid_from
