-- A previsão da mudança do preço em Portugal à segunda-feira, e o que aconteceu.
--
-- O preço de segunda-feira acompanha os mercados internacionais da semana anterior. Para cada
-- segunda-feira, a mudança do preço sem impostos (euros por 1000 L) prevê-se com a mudança da
-- cotação média em Nova Iorque nas duas semanas antes:
--   mudança = beta_last_week × (média da semana anterior − média da semana antes dessa)
--           + beta_week_before × (a mesma diferença uma semana antes)
-- Os coeficientes vêm do seed forecast_coefficients (ajustados com scripts/fit_forecast.py).
-- A previsão em euros por litro já leva o IVA, mas não uma eventual mudança do ISP: em
-- `actual_change` está a mudança do preço com impostos que o boletim publicou, ISP incluído.
with

weeks as (select * from {{ ref('int_market_weeks') }}),
coefficients as (select * from {{ ref('forecast_coefficients') }}),
prices as (
    select week, product, price_with_tax, price_without_tax, vat_rate
    from {{ ref('fct_fuel_prices') }}
    where country_code = 'PT'
),

targets as (
    -- Cada segunda-feira com as três semanas de cotações antes, até à próxima segunda-feira.
    select
        cast(w1.week + interval 7 day as date) as target_week,
        w1.product,
        coefficients.beta_last_week * (w1.eur_per_1000l - w2.eur_per_1000l)
            + coefficients.beta_week_before * (w2.eur_per_1000l - w3.eur_per_1000l)
            as predicted_change_before_tax,
        w1.days as market_days_last_week,
        w1.last_day as last_market_day
    from weeks as w1
    inner join weeks as w2
        on w2.product = w1.product and w2.week = w1.week - interval 7 day
    inner join weeks as w3
        on w3.product = w1.product and w3.week = w1.week - interval 14 day
    inner join coefficients on coefficients.product = w1.product
),

with_prices as (
    select
        targets.*,
        now.price_with_tax - previous.price_with_tax as actual_change_with_tax_1000l,
        now.price_without_tax - previous.price_without_tax as actual_change_before_tax,
        -- O IVA da semana prevista, ou o último conhecido.
        coalesce(now.vat_rate, last_vat.vat_rate) as vat_rate
    from targets
    left join prices as now
        on now.product = targets.product and now.week = targets.target_week
    left join prices as previous
        on previous.product = targets.product
        and previous.week = targets.target_week - interval 7 day
    asof left join prices as last_vat
        on last_vat.product = targets.product and last_vat.week <= targets.target_week
)

select
    target_week,
    product,
    -- Euros por litro, com IVA.
    predicted_change_before_tax * (1 + vat_rate / 100) / 1000 as predicted_change,
    actual_change_before_tax * (1 + vat_rate / 100) / 1000 as actual_change_before_tax,
    actual_change_with_tax_1000l / 1000 as actual_change,
    market_days_last_week,
    last_market_day,
    actual_change_before_tax is not null as is_known
from with_prices
