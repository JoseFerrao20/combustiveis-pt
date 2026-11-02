---
title: Análises
sidebar_position: 2
description: Quanto do preço dos combustíveis são impostos, a previsão para segunda-feira, Portugal comparado com a Europa, e como se fazem as contas.
og:
  image: https://joseferrao20.github.io/combustiveis-pt/og.png
---

Para quem quer ir além do posto mais barato. Cada cartão abre uma análise.

```sql cartoes
-- O número principal de cada análise, para os cartões (gasolina 95, última semana do boletim).
with
pt as (
    select week, price, tax_share
    from combustiveis.precos
    where country_code = 'PT' and product = 'euro95'
    order by week desc
    limit 1
),
es as (
    select price
    from combustiveis.precos
    where country_code = 'ES' and product = 'euro95' and week = (select week from pt)
),
previsao as (
    select target_week, predicted_change
    from combustiveis.previsao
    where product = 'euro95'
    order by target_week desc
    limit 1
),
acerto as (
    select avg(abs(predicted_change - actual_change)) * 100 as erro, count(*) as semanas
    from combustiveis.previsao
    where is_known
),
base as (
select
    (select week from pt) as semana,
    (select tax_share from pt) as parte_impostos,
    ((select price from pt) - (select price from es)) * 100 as face_espanha,
    case
        when ((select price from pt) - (select price from es)) > 0 then 'mais cara do que em Espanha'
        else 'mais barata do que em Espanha'
    end as face_espanha_texto,
    case
        when round((select predicted_change from previsao) * 100, 1) > 0 then '▲ '
        when round((select predicted_change from previsao) * 100, 1) < 0 then '▼ '
        else '= '
    end || replace(printf('%.1f', abs((select predicted_change from previsao) * 100)), '.', ',') || ' c'
        as previsao_texto,
    (select target_week from previsao) as previsao_semana,
    case
        when (select semanas from acerto) > 0
            then 'Erro médio de ' || replace(printf('%.1f', (select erro from acerto)), '.', ',')
                || ' cêntimos nas semanas desde 2024.'
        else 'Ainda sem semanas para comparar.'
    end as acerto_texto,
    (select count(distinct week) from combustiveis.precos) as semanas,
    (select min(week) from combustiveis.precos) as desde,
    (select count(distinct station_id) from combustiveis.postos) as postos
)
-- As frases dos cartões, já com a pontuação (o Value do Evidence deixa um espaço a seguir).
select
    *,
    'do preço da gasolina 95 é ISP e IVA (semana de ' || strftime(semana, '%d/%m/%Y')
        || '). Semana a semana desde 2005.' as impostos_texto,
    'na gasolina 95, a ' || strftime(previsao_semana, '%d/%m') || ', a partir dos mercados. '
        || acerto_texto as previsao_frase,
    'por litro: a gasolina 95 em Portugal, ' || face_espanha_texto || '. Com a média da União Europeia.'
        as espanha_frase,
    'do boletim europeu desde ' || strftime(desde, '%Y') || ', e '
        || replace(format('{:,}', postos), ',', ' ')
        || ' postos em Portugal. De onde vêm os dados, as contas e os limites.' as metodo_frase
from base
```

<div class="cartoes">
<a class="cartao" href="/combustiveis-pt/analises/impostos/">
<span class="cartao-titulo">Quanto do preço é imposto?</span>
<span class="cartao-numero"><Value data={cartoes} column=parte_impostos fmt=pct0 /></span>
<span class="cartao-texto"><Value data={cartoes} column=impostos_texto /></span>
</a>
<a class="cartao" href="/combustiveis-pt/analises/previsao/">
<span class="cartao-titulo">Previsão para segunda-feira</span>
<span class="cartao-numero"><Value data={cartoes} column=previsao_texto /></span>
<span class="cartao-texto"><Value data={cartoes} column=previsao_frase /></span>
</a>
<a class="cartao" href="/combustiveis-pt/analises/comparacao/">
<span class="cartao-titulo">Portugal e a Europa</span>
<span class="cartao-numero"><Value data={cartoes} column=face_espanha fmt='+0.0 "c";-0.0 "c"' /></span>
<span class="cartao-texto"><Value data={cartoes} column=espanha_frase /></span>
</a>
<a class="cartao" href="/combustiveis-pt/analises/metodo/">
<span class="cartao-titulo">Como se calcula</span>
<span class="cartao-numero"><Value data={cartoes} column=semanas fmt="#,##0" /> semanas</span>
<span class="cartao-texto"><Value data={cartoes} column=metodo_frase /></span>
</a>
</div>
