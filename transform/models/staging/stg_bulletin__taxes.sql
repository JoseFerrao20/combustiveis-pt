-- IVA em %; ISP e outros impostos na moeda nacional por 1000 L (ou t), desde valid_from.
select
    tax,
    country as country_code,
    since as valid_from,
    product,
    value
from {{ source('bulletin', 'taxes') }}
