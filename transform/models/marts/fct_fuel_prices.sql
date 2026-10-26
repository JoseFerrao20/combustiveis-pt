-- O preço de cada semana, país e produto, e a parte que é imposto.
--
-- A decomposição usa só os preços publicados e a taxa do IVA, por isso soma sempre o preço:
--   IVA                    = preço − preço ÷ (1 + taxa)
--   ISP e outros impostos  = preço ÷ (1 + taxa) − preço sem impostos
-- As tabelas de ISP e de outros impostos do boletim nem sempre explicam essa parte (há
-- períodos com valores em falta ou trocados entre as duas): a diferença fica em
-- tax_tables_gap, para se ver em vez de se esconder.
with

prices as (select * from {{ ref('int_prices_pivoted') }}),
taxes as (select * from {{ ref('int_taxes_in_force') }}),
countries as (select * from {{ ref('countries') }}),

decomposed as (
    select
        prices.week,
        prices.country_code,
        prices.product,
        prices.price_with_tax,
        prices.price_without_tax,
        prices.price_with_tax - prices.price_without_tax as taxes_total,
        taxes.vat_rate,
        prices.price_with_tax - prices.price_with_tax / (1 + taxes.vat_rate / 100) as vat_amount,
        prices.price_with_tax / (1 + taxes.vat_rate / 100) - prices.price_without_tax
            as excise_and_other_taxes,
        -- Os impostos vêm na moeda nacional: só se comparam com os preços (em euros) quando o
        -- país já usava o euro nessa semana.
        case when prices.week >= countries.euro_since then taxes.excise end as reported_excise,
        case when prices.week >= countries.euro_since then taxes.other_taxes end
            as reported_other_taxes
    from prices
    inner join countries on countries.country_code = prices.country_code
    left join taxes
        on taxes.week = prices.week
        and taxes.country_code = prices.country_code
        and taxes.product = prices.product
)

select
    *,
    taxes_total / nullif(price_with_tax, 0) as tax_share,
    case
        when reported_excise is not null
            then excise_and_other_taxes - reported_excise - coalesce(reported_other_taxes, 0)
    end as tax_tables_gap
from decomposed
