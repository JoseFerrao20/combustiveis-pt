-- Num país (não nas médias da UE, que juntam países diferentes em cada produto), o preço com
-- impostos nunca é menor do que o preço sem impostos. Os erros já conhecidos do boletim estão
-- no seed known_source_errors, com a explicação.
select fuel.*
from {{ ref('fct_fuel_prices') }} as fuel
inner join {{ ref('countries') }} as countries using (country_code)
anti join {{ ref('known_source_errors') }} as known using (country_code, product, week)
where countries.kind = 'country'
    and fuel.price_with_tax < fuel.price_without_tax
