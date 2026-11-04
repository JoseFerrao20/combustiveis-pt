-- Os preços máximos dos Açores e da Madeira, com os tipos certos (o CSV pode vir só com o
-- cabeçalho, antes da primeira leitura).
select
    cast(region as varchar) as region,
    cast(fuel as varchar) as fuel,
    cast(valid_from as date) as valid_from,
    cast(price as decimal(6, 3)) as price,
    cast(act as varchar) as act,
    cast(published as date) as published,
    cast(source_url as varchar) as source_url
from {{ source('ilhas', 'max_prices') }}
