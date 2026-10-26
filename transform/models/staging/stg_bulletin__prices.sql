-- Preços médios nacionais, em euros por 1000 L (por tonelada nos fuelóleos).
select
    week,
    country as country_code,
    product,
    tax_status,
    value as price
from {{ source('bulletin', 'prices') }}
