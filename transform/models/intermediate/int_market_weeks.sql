-- A média semanal (segunda a domingo) das cotações da gasolina e do gasóleo em Nova Iorque, em
-- euros por 1000 L, como os preços do boletim. Cada dia usa o último câmbio conhecido (o FRED
-- publica o câmbio com uns dias de atraso). `days` diz quantos dias com cotação tem a semana:
-- a semana em curso fica incompleta.
with

markets as (select * from {{ ref('stg_fred__markets') }}),

fx as (select day, value as usd_per_eur from markets where series = 'DEXUSEU'),

products as (
    select series, 'euro95' as product from (values ('DGASNYH')) as t (series)
    union all
    select 'DDFUELNYH', 'diesel'
),

daily as (
    -- Dólares por galão → euros por 1000 L (um galão americano tem 3,785411784 L).
    select
        products.product,
        markets.series,
        markets.day,
        markets.value / fx.usd_per_eur / 3.785411784 * 1000 as eur_per_1000l
    from markets
    inner join products using (series)
    asof inner join fx on fx.day <= markets.day
)

select
    product,
    series as market_series,
    cast(date_trunc('week', day) as date) as week,
    avg(eur_per_1000l) as eur_per_1000l,
    count(*) as days,
    max(day) as last_day
from daily
group by all
