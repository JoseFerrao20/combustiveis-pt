{{ config(severity='warn') }}
-- Aviso: preços de um posto fora do intervalo plausível (0,50 € a 4 € por litro). O preço vem
-- como o posto o comunicou; um valor assim é quase sempre um erro de quem o escreveu.
select snapshot_date, station_id, brand, fuel, price
from {{ ref('fct_station_prices') }}
where price < 0.5 or price > 4
