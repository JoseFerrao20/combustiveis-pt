-- Preços de cada posto, por dia de fotografia. O updated_at é a hora (de Lisboa) a que o posto
-- comunicou o preço à DGEG; um preço pode ficar meses sem mudar.
select
    snapshot_date,
    station_id,
    name as station_name,
    brand,
    station_type,
    district,
    municipality,
    address,
    locality,
    postal_code,
    latitude,
    longitude,
    fuel,
    price,
    updated_at,
    date_diff('day', cast(updated_at as date), snapshot_date) as days_since_update
from {{ source('dgeg', 'station_prices') }}
