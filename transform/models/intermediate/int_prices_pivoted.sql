-- Uma linha por semana, país e produto, com o preço com e sem impostos lado a lado.
select
    week,
    country_code,
    product,
    max(price) filter (where tax_status = 'with_tax') as price_with_tax,
    max(price) filter (where tax_status = 'without_tax') as price_without_tax
from {{ ref('stg_bulletin__prices') }}
group by all
