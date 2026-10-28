---
sidebar_position: 1
title: Portugal e a Europa
---

```sql combustiveis
select distinct product, fuel
from combustiveis.precos
order by product = 'lpg', product = 'diesel'
```

<Dropdown data={combustiveis} name=produto value=product label=fuel defaultValue="euro95" title="Combustível" />

```sql evolucao
select week, country, price
from combustiveis.precos
where country_code in ('PT', 'ES', 'EU')
    and product = '${inputs.produto.value}'
order by week
```

<LineChart
    data={evolucao}
    x=week
    y=price
    series=country
    seriesColors={{'Portugal': '#15803d', 'Espanha': '#d97706', 'União Europeia (média)': '#2563eb'}}
    title="Preço por litro: Portugal, Espanha e a média da UE"
    yFmt='0.00 "€"'
    xAxisTitle=false
    yAxisTitle=false
/>

```sql ultima_semana
select max(week) as week
from combustiveis.precos
where product = '${inputs.produto.value}'
```

## Na semana de <Value data={ultima_semana} column=week fmt="dd/mm/yyyy" />

```sql paises
select
    country,
    price_without_tax,
    taxes_total,
    price_without_tax as "Produto",
    taxes_total as "Impostos",
    price,
    tax_share,
    country_code = 'PT' as portugal
from combustiveis.precos
where product = '${inputs.produto.value}'
    and week = (select week from ${ultima_semana})
    and not is_average
order by price desc
```

<BarChart
    data={paises}
    x=country
    y={['Produto', 'Impostos']}
    colorPalette={['#64748b', '#d97706']}
    swapXY=true
    sort=false
    title="Preço por litro em cada país, dividido em produto e impostos"
    yFmt='0.00 "€"'
    xAxisTitle=false
    yAxisTitle=false
    chartAreaHeight=520
/>

<DataTable data={paises} rows=30>
    <Column id=country title="País" />
    <Column id=price title="Preço (€/L)" fmt='0.000' />
    <Column id=price_without_tax title="Produto (€/L)" fmt='0.000' />
    <Column id=taxes_total title="Impostos (€/L)" fmt='0.000' />
    <Column id=tax_share title="Parte do preço" fmt=pct1 />
</DataTable>

O preço antes de impostos também muda de país para país (logística, concorrência e margens), não só os impostos.

