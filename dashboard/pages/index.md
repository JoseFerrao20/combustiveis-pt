---
title: Quanto do preço é imposto?
---

Preços semanais dos combustíveis em Portugal desde 2005, a partir do [Weekly Oil Bulletin](https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en) da Comissão Europeia. Os valores são médias nacionais em euros por litro, não os preços de um posto.

```sql combustiveis
select distinct product, fuel
from combustiveis.precos
order by product = 'lpg', product = 'diesel'
```

<Dropdown data={combustiveis} name=produto value=product label=fuel defaultValue="euro95" title="Combustível" />

```sql ultima_semana
select *
from combustiveis.precos
where country_code = 'PT'
    and product = '${inputs.produto.value}'
order by week desc
limit 1
```

## Semana de <Value data={ultima_semana} column=week fmt="dd/mm/yyyy" />

<BigValue data={ultima_semana} value=price title="Preço por litro" fmt='0.000 "€"' />
<BigValue data={ultima_semana} value=taxes_total title="Impostos" fmt='0.000 "€"' />
<BigValue data={ultima_semana} value=tax_share title="Parte do preço" fmt=pct1 />

```sql decomposicao
select 'Produto (antes de impostos)' as parte, price_without_tax as valor, 1 as ordem from ${ultima_semana}
union all
select 'ISP e outros impostos', excise_and_other_taxes, 2 from ${ultima_semana}
union all
select 'IVA', vat_amount, 3 from ${ultima_semana}
order by ordem
```

<DataTable data={decomposicao} totalRow=true>
    <Column id=parte title="Parte do preço" totalAgg="Preço" />
    <Column id=valor title="€ por litro" fmt='0.000' />
</DataTable>

## Desde 2005

```sql historico
select week, 'Produto' as parte, price_without_tax as valor
from combustiveis.precos
where country_code = 'PT' and product = '${inputs.produto.value}'
union all
select week, 'ISP e outros impostos', excise_and_other_taxes
from combustiveis.precos
where country_code = 'PT' and product = '${inputs.produto.value}'
union all
select week, 'IVA', vat_amount
from combustiveis.precos
where country_code = 'PT' and product = '${inputs.produto.value}'
order by week
```

<AreaChart
    data={historico}
    x=week
    y=valor
    series=parte
    seriesOrder={['Produto', 'ISP e outros impostos', 'IVA']}
    title="Preço por litro, dividido em produto e impostos"
    yFmt='0.00 "€"'
    xAxisTitle=false
    yAxisTitle=false
/>

```sql peso
select week, tax_share
from combustiveis.precos
where country_code = 'PT' and product = '${inputs.produto.value}'
order by week
```

<LineChart
    data={peso}
    x=week
    y=tax_share
    title="Parte do preço que é imposto"
    yFmt=pct0
    yMin=0
    xAxisTitle=false
    yAxisTitle=false
/>

Quando o petróleo fica mais barato, os impostos pesam mais, porque o ISP é um valor fixo por litro e não uma percentagem. As descidas do ISP de 2022 notam-se no gráfico de cima.

