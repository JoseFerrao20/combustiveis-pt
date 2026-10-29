---
title: Postos acompanhados
sidebar_position: 1
description: Alguns postos seguidos dia a dia, comparados com os concorrentes a 5 km.
og:
  image: https://joseferrao20.github.io/combustiveis-pt/og.png
---

Alguns postos seguidos de perto, dia a dia: o preço, comparado com o dos concorrentes num raio de 5 km (em linha reta) e com a média do concelho. Os preços são os que cada posto comunica à Direção-Geral de Energia e Geologia ([precoscombustiveis.dgeg.gov.pt](https://precoscombustiveis.dgeg.gov.pt)).

```sql postos_lista
select distinct station_id, label from combustiveis.acompanhados order by label
```

```sql combustiveis
select distinct fuel, fuel_name
from combustiveis.acompanhados
order by fuel = 'gpl', fuel = 'gasoleo', fuel = 'gasolina_98'
```

<Dropdown data={postos_lista} name=posto value=station_id label=label title="Posto" />
<Dropdown data={combustiveis} name=combustivel value=fuel label=fuel_name defaultValue="gasolina_95" title="Combustível" />

```sql historico
select *
from combustiveis.acompanhados
where station_id = '${inputs.posto.value}' and fuel = '${inputs.combustivel.value}'
order by snapshot_date
```

```sql hoje
select
    *,
    (price - competitors_avg_price) * 100 as vs_concorrentes,
    (price - municipality_avg_price) * 100 as vs_concelho,
    printf('%dº de %d', rank_5km::integer, coalesce(competitors, 0)::integer + 1) as posicao,
    location || ', concelho de ' || municipality || '. Preço atualizado a '
        || strftime(updated_at, '%d/%m/%Y, %H:%M') || ', na fotografia de '
        || strftime(snapshot_date, '%d/%m/%Y') || '.' as descricao
from ${historico}
order by snapshot_date desc
limit 1
```

{#if hoje.length > 0}

## <Value data={hoje} column=station_name />

<p class="mb-4"><Value data={hoje} column=descricao /></p>

<BigValue data={hoje} value=price title="Preço" fmt='0.000 "€"' />
<BigValue data={hoje} value=posicao title="Posição entre os postos a 5 km" />
<BigValue data={hoje} value=vs_concorrentes title="Face à média a 5 km (cêntimos)" fmt='+0.0;-0.0' />
<BigValue data={hoje} value=vs_concelho title="Face à média do concelho (cêntimos)" fmt='+0.0;-0.0' />

A posição conta os concorrentes a 5 km com o mesmo combustível e o preço atualizado nos últimos 30 dias; 1º é o mais barato, e um empate não conta como mais barato.

{:else}

Este posto não tem preço deste combustível.

{/if}

## Ao longo do tempo

```sql evolucao
select snapshot_date as dia, 'Este posto' as serie, price as preco from ${historico}
union all
select snapshot_date, 'Média a 5 km', competitors_avg_price from ${historico}
union all
select snapshot_date, 'Mais barato a 5 km', competitors_min_price from ${historico}
union all
select snapshot_date, 'Média do concelho', municipality_avg_price from ${historico}
order by dia
```

{#if historico.length > 5}

<LineChart
    data={evolucao}
    x=dia
    y=preco
    series=serie
    seriesOrder={['Este posto', 'Mais barato a 5 km', 'Média a 5 km', 'Média do concelho']}
    seriesColors={{'Este posto': '#b91c1c', 'Mais barato a 5 km': '#d97706', 'Média a 5 km': '#64748b', 'Média do concelho': '#94a3b8'}}
    title="Preço por litro"
    yFmt='0.000 "€"'
    xAxisTitle=false
    yAxisTitle=false
/>

{:else}

O gráfico aparece quando houver mais dias de fotografias. A DGEG só mostra o preço em vigor, por isso o histórico começa a 28/10/2026, com uma fotografia por dia.

{/if}

<DataTable data={historico} sort="snapshot_date desc" rows=10 emptySet="pass" emptyMessage="Sem preços deste combustível.">
    <Column id=snapshot_date title="Dia" fmt="dd/mm/yyyy" />
    <Column id=price title="Preço (€/L)" fmt='0.000' />
    <Column id=rank_5km title="Posição a 5 km" />
    <Column id=competitors_min_price title="Mais barato a 5 km" fmt='0.000' />
    <Column id=competitors_avg_price title="Média a 5 km" fmt='0.000' />
    <Column id=municipality_avg_price title="Média do concelho" fmt='0.000' />
    <Column id=updated_at title="Atualizado" fmt='dd/mm/yyyy hh:mm' />
</DataTable>

## Os concorrentes a 5 km

```sql concorrentes
select station_name, brand, distance_km, price as "Preço (€/L)", updated_at, latitude, longitude
from combustiveis.acompanhados_concorrentes
where station_id = '${inputs.posto.value}'
    and fuel = '${inputs.combustivel.value}'
    and is_current
order by "Preço (€/L)", distance_km
```

O posto acompanhado é o ponto vermelho; os concorrentes têm a cor do preço.

<BaseMap
    height=450
    basemap={'https://tile.openstreetmap.org/{z}/{x}/{y}.png'}
    attribution={'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}
>
    <Points
        data={concorrentes}
        lat=latitude
        long=longitude
        value='Preço (€/L)'
        valueFmt='0.000'
        pointName=station_name
        tooltip={[
            {id: 'station_name', showColumnName: false, valueClass: 'font-semibold'},
            {id: 'brand', title: 'Marca'},
            {id: 'Preço (€/L)', title: 'Preço', fmt: '0.000 "€"'},
            {id: 'distance_km', title: 'Distância (km)', fmt: '0.0'},
            {id: 'updated_at', title: 'Atualizado', fmt: 'dd/mm/yyyy hh:mm'}
        ]}
    />
    <Points
        data={hoje}
        lat=latitude
        long=longitude
        color='#b91c1c'
        size=10
        legend=false
        pointName=station_name
        tooltip={[
            {id: 'station_name', showColumnName: false, valueClass: 'font-semibold'},
            {id: 'price', title: 'Preço', fmt: '0.000 "€"'},
            {id: 'updated_at', title: 'Atualizado', fmt: 'dd/mm/yyyy hh:mm'}
        ]}
    />
</BaseMap>

<DataTable data={concorrentes} rows=15 search=true emptySet="pass" emptyMessage="Nenhum concorrente a 5 km com este combustível.">
    <Column id=station_name title="Posto" />
    <Column id=brand title="Marca" />
    <Column id=distance_km title="Distância (km)" fmt='0.0' />
    <Column id='Preço (€/L)' fmt='0.000' contentType=colorscale colorScale=negative />
    <Column id=updated_at title="Atualizado" fmt='dd/mm/yyyy hh:mm' />
</DataTable>

Distâncias em linha reta. Ficam de fora os preços com mais de 30 dias.

<p class="text-sm text-base-content-muted">Fonte: Direção-Geral de Energia e Geologia, Preços dos Combustíveis Online. Preços comunicados pelos postos, com a data e hora de atualização de cada um. Para acompanhar outro posto, basta juntá-lo ao seed <code>tracked_stations</code> do projeto.</p>
