{{ config(
    materialized='external',
    location=env_var('FORECAST_EXPORT_PATH', 'data/price_forecast.parquet'),
) }}
-- A previsão para as segundas-feiras desde 2024 (o período de teste, fora do ajuste) e para a
-- próxima, para o painel: em euros por litro, com IVA, sem mudanças do ISP.
select
    forecasts.*,
    products.name as product_name,
    coefficients.trained_from,
    coefficients.trained_to
from {{ ref('fct_price_forecasts') }} as forecasts
inner join {{ ref('products') }} as products using (product)
inner join {{ ref('forecast_coefficients') }} as coefficients using (product)
where forecasts.target_week > coefficients.trained_to
