-- O preço de cada posto em cada dia de fotografia, com o grupo da marca. Um preço que o posto
-- não atualiza há mais de 30 dias fica marcado (is_current = false) e não entra nas médias.
with

prices as (select * from {{ ref('stg_dgeg__station_prices') }}),
segments as (select * from {{ ref('dgeg_brand_segments') }})

select
    prices.*,
    coalesce(segments.segment, 'Outras marcas') as brand_segment,
    prices.days_since_update <= 30 as is_current
from prices
left join segments using (brand)
