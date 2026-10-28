---
title: Postos em Portugal
sidebar_position: 2
---

O preço de cada posto de Portugal continental, tal como o posto o comunica à Direção-Geral de Energia e Geologia ([precoscombustiveis.dgeg.gov.pt](https://precoscombustiveis.dgeg.gov.pt)). As médias usam só os preços atualizados nos últimos 30 dias.

```sql combustiveis
select distinct fuel, fuel_name
from combustiveis.postos
order by fuel = 'gpl', fuel = 'gasoleo', fuel = 'gasolina_98'
```

<Dropdown data={combustiveis} name=combustivel value=fuel label=fuel_name defaultValue="gasolina_95" title="Combustível" />

```sql resumo
select
    max(snapshot_date) as dia,
    count(*) filter (where is_current) as postos,
    avg(price) filter (where is_current) as media,
    min(price) filter (where is_current) as minimo,
    max(price) filter (where is_current) as maximo,
    max(updated_at) as ultima_atualizacao
from combustiveis.postos
where fuel = '${inputs.combustivel.value}'
```

## Dia <Value data={resumo} column=dia fmt="dd/mm/yyyy" />

<BigValue data={resumo} value=postos title="Postos" fmt="#,##0" />
<BigValue data={resumo} value=media title="Preço médio" fmt='0.000 "€"' />
<BigValue data={resumo} value=minimo title="Mais barato" fmt='0.000 "€"' />
<BigValue data={resumo} value=maximo title="Mais caro" fmt='0.000 "€"' />

```sql mapa
select station_name, brand, municipality, price as "Preço (€/L)", latitude, longitude, updated_at
from combustiveis.postos
where fuel = '${inputs.combustivel.value}'
    and is_current
    and latitude is not null
```

<PointMap
    data={mapa}
    lat=latitude
    long=longitude
    value='Preço (€/L)'
    valueFmt='0.000'
    pointName=station_name
    height=600
    startingLat=39.6
    startingLong=-8.0
    startingZoom=7
    tooltip={[
        {id: 'station_name', showColumnName: false, valueClass: 'font-semibold'},
        {id: 'brand', title: 'Marca'},
        {id: 'municipality', title: 'Concelho'},
        {id: 'Preço (€/L)', title: 'Preço', fmt: '0.000 "€"'},
        {id: 'updated_at', title: 'Atualizado', fmt: 'dd/mm/yyyy hh:mm'}
    ]}
/>

## Por grupo de marcas

```sql grupos
select
    grupos.label as grupo,
    grupos.stations as postos,
    grupos.avg_price as media,
    (grupos.avg_price - pais.avg_price) * 100 as diferenca
from combustiveis.postos_diario as grupos
inner join combustiveis.postos_diario as pais
    on pais.snapshot_date = grupos.snapshot_date
    and pais.fuel = grupos.fuel
    and pais.dimension = 'Portugal'
where grupos.fuel = '${inputs.combustivel.value}'
    and grupos.dimension = 'Grupo de marcas'
    and grupos.snapshot_date = (select max(snapshot_date) from combustiveis.postos_diario)
order by diferenca
```

<BarChart
    data={grupos}
    x=grupo
    y=diferenca
    swapXY=true
    sort=false
    colorPalette={['#d97706']}
    title="Diferença para o preço médio do país, em cêntimos por litro"
    yFmt='+0.0;-0.0'
    labels=true
    xAxisTitle=false
    yAxisTitle=false
/>

<DataTable data={grupos}>
    <Column id=grupo title="Grupo de marcas" />
    <Column id=postos title="Postos" fmt="#,##0" />
    <Column id=media title="Preço médio (€/L)" fmt='0.000' />
    <Column id=diferenca title="Diferença (cêntimos)" fmt='+0.0;-0.0' />
</DataTable>

Os hiper e supermercados são Intermarché, Pingo Doce, Auchan, E.Leclerc e Recheio. As petrolíferas são Galp, Repsol, BP, Cepsa, Moeve, Shell, Esso e Q8. "Sem marca" são os postos que a DGEG regista como "Genérico".

```sql tipos
select station_type as tipo, count(*) as postos, avg(price) as media
from combustiveis.postos
where fuel = '${inputs.combustivel.value}' and is_current
group by all
order by media
```

<DataTable data={tipos}>
    <Column id=tipo title="Tipo de posto" />
    <Column id=postos title="Postos" fmt="#,##0" />
    <Column id=media title="Preço médio (€/L)" fmt='0.000' />
</DataTable>

## Por marca

```sql marcas
select label as marca, stations as postos, avg_price as media, min_price as minimo, max_price as maximo
from combustiveis.postos_diario
where fuel = '${inputs.combustivel.value}'
    and dimension = 'Marca'
    and snapshot_date = (select max(snapshot_date) from combustiveis.postos_diario)
    and stations >= 10
order by media
```

<DataTable data={marcas} rows=30 emptySet="pass" emptyMessage="Nenhuma marca com pelo menos 10 postos.">
    <Column id=marca title="Marca" />
    <Column id=postos title="Postos" fmt="#,##0" />
    <Column id=media title="Média (€/L)" fmt='0.000' contentType=colorscale colorScale=negative />
    <Column id=minimo title="Mínimo" fmt='0.000' />
    <Column id=maximo title="Máximo" fmt='0.000' />
</DataTable>

Só as marcas com pelo menos 10 postos.

## Por distrito

```sql distritos
select label as distrito, stations as postos, avg_price as media
from combustiveis.postos_diario
where fuel = '${inputs.combustivel.value}'
    and dimension = 'Distrito'
    and snapshot_date = (select max(snapshot_date) from combustiveis.postos_diario)
order by media
```

<DataTable data={distritos} rows=20>
    <Column id=distrito title="Distrito" />
    <Column id=postos title="Postos" fmt="#,##0" />
    <Column id=media title="Média (€/L)" fmt='0.000' contentType=colorscale colorScale=negative />
</DataTable>

## Os mais baratos e os mais caros

```sql baratos
select station_name, brand, municipality, district, price, updated_at
from combustiveis.postos
where fuel = '${inputs.combustivel.value}' and is_current
order by price, station_name
limit 10
```

```sql caros
select station_name, brand, municipality, district, price, updated_at
from combustiveis.postos
where fuel = '${inputs.combustivel.value}' and is_current
order by price desc, station_name
limit 10
```

<Tabs>
    <Tab label="Mais baratos">
        <DataTable data={baratos}>
            <Column id=station_name title="Posto" />
            <Column id=brand title="Marca" />
            <Column id=municipality title="Concelho" />
            <Column id=price title="Preço (€/L)" fmt='0.000' />
            <Column id=updated_at title="Atualizado" fmt='dd/mm/yyyy hh:mm' />
        </DataTable>
    </Tab>
    <Tab label="Mais caros">
        <DataTable data={caros}>
            <Column id=station_name title="Posto" />
            <Column id=brand title="Marca" />
            <Column id=municipality title="Concelho" />
            <Column id=price title="Preço (€/L)" fmt='0.000' />
            <Column id=updated_at title="Atualizado" fmt='dd/mm/yyyy hh:mm' />
        </DataTable>
    </Tab>
</Tabs>

## Ao longo do tempo

```sql evolucao
select snapshot_date as dia, label as grupo, avg_price as media
from combustiveis.postos_diario
where fuel = '${inputs.combustivel.value}'
    and dimension in ('Portugal', 'Grupo de marcas')
order by dia
```

{#if evolucao.length > 5}

<LineChart
    data={evolucao}
    x=dia
    y=media
    series=grupo
    title="Preço médio por litro, por grupo de marcas"
    yFmt='0.000 "€"'
    xAxisTitle=false
    yAxisTitle=false
/>

{:else}

O gráfico aparece quando houver mais dias de fotografias.

{/if}

A DGEG só mostra o preço em vigor: o histórico guarda-se aqui, com uma fotografia por dia desde 28/10/2026.

<p class="text-sm text-base-content-muted">Fonte: Direção-Geral de Energia e Geologia, Preços dos Combustíveis Online. Preços comunicados pelos postos; a data e hora de atualização de cada preço está no mapa e nas tabelas. Última atualização recebida: <Value data={resumo} column=ultima_atualizacao fmt="dd/mm/yyyy hh:mm" /></p>
