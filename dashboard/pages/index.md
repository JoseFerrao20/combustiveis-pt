---
title: Combustível mais barato
description: O preço de cada posto de combustível em Portugal, do mais barato para o mais caro, com um mapa e a opção de ver os mais baratos perto de si.
og:
  title: Combustível mais barato perto de si
  image: https://joseferrao20.github.io/combustiveis-pt/og.png
---

O preço de cada posto de Portugal continental, atualizado todos os dias. Carregue em **Perto de mim**, por baixo, para ver os mais baratos à sua volta, ou escolha o distrito e o concelho.

```sql combustiveis
select distinct fuel, fuel_name
from combustiveis.postos
order by fuel = 'gpl', fuel = 'gasoleo', fuel = 'gasolina_98'
```

```sql distritos_lista
select distinct district from combustiveis.postos order by district
```

```sql concelhos_lista
select distinct municipality
from combustiveis.postos
where district like '${inputs.distrito.value}'
order by municipality
```

```sql previsao
-- A previsão para a próxima segunda-feira (página Análises → Previsão para segunda-feira).
select
    'Previsão para segunda-feira, ' || strftime(max(target_week), '%d/%m') || ': '
        || string_agg(
            product_name || ' ' || case
                when round(predicted_change * 100, 1) > 0 then '▲ +' || replace(printf('%.1f', predicted_change * 100), '.', ',')
                when round(predicted_change * 100, 1) < 0 then '▼ −' || replace(printf('%.1f', -predicted_change * 100), '.', ',')
                else '= 0,0'
            end || ' cêntimos',
            ', ' order by product = 'diesel'
        ) || ' por litro (estimativa, sem mudanças do ISP).'
        -- Na segunda-feira, a fotografia da DGEG já diz quanto os postos mudaram.
        || coalesce(
            ' Nos postos, a mudança foi de ' || string_agg(
                product_name || ' ' || case
                    -- Sem fotografia de segunda-feira, o valor é nulo e o produto não entra.
                    when dgeg_change is null then null
                    when round(dgeg_change * 100, 1) > 0 then '▲ +' || replace(printf('%.1f', dgeg_change * 100), '.', ',')
                    when round(dgeg_change * 100, 1) < 0 then '▼ −' || replace(printf('%.1f', -dgeg_change * 100), '.', ',')
                    else '= 0,0'
                end,
                ', ' order by product = 'diesel'
            ) || ' cêntimos.',
            ''
        ) as texto
from combustiveis.previsao
where target_week = (select max(target_week) from combustiveis.previsao)
```

{#if previsao.length > 0 && previsao[0].texto}
<p class="previsao-segunda"><Value data={previsao} column=texto /> Ver como se calcula em Análises.</p>
{/if}

<Dropdown data={combustiveis} name=combustivel value=fuel label=fuel_name defaultValue="gasolina_95" title="Combustível" />
<Dropdown data={distritos_lista} name=distrito value=district title="Distrito">
    <DropdownOption value="%" valueLabel="Todos" />
</Dropdown>
<Dropdown data={concelhos_lista} name=concelho value=municipality title="Concelho">
    <DropdownOption value="%" valueLabel="Todos" />
</Dropdown>

```sql zona
-- Só as colunas que as consultas abaixo usam: o Evidence guarda o resultado de cada consulta no
-- site, e a página fica mais leve.
select
    snapshot_date, station_name, brand, brand_segment, station_type, district, municipality,
    latitude, longitude, price, updated_at, is_current,
    change_since_previous, last_change_date, history_7d
from combustiveis.postos
where fuel = '${inputs.combustivel.value}'
    and district like '${inputs.distrito.value}'
    and municipality like '${inputs.concelho.value}'
```

```sql mapa
select
    station_name, brand, municipality, price, latitude, longitude, updated_at,
    change_since_previous, last_change_date, history_7d
from ${zona}
where is_current and latitude is not null
```

<MapaPostos data={mapa} />

```sql resumo
select
    max(snapshot_date) as dia,
    count(*) filter (where is_current) as postos,
    avg(price) filter (where is_current) as media,
    min(price) filter (where is_current) as minimo,
    max(price) filter (where is_current) as maximo,
    max(updated_at) as ultima_atualizacao
from ${zona}
```

## Resumo do dia <Value data={resumo} column=dia fmt="dd/mm/yyyy" />

<BigValue data={resumo} value=postos title="Postos" fmt="#,##0" />
<BigValue data={resumo} value=media title="Preço médio" fmt='0.000 "€"' />
<BigValue data={resumo} value=minimo title="Mais barato" fmt='0.000 "€"' />
<BigValue data={resumo} value=maximo title="Mais caro" fmt='0.000 "€"' />

Os preços são os que cada posto comunica à Direção-Geral de Energia e Geologia ([precoscombustiveis.dgeg.gov.pt](https://precoscombustiveis.dgeg.gov.pt)); as médias usam só os atualizados nos últimos 30 dias.

## Por grupo de marcas

```sql grupos
with zona_atual as (select * from ${zona} where is_current)
select
    brand_segment as grupo,
    count(*) as postos,
    avg(price) as media,
    (avg(price) - (select avg(price) from zona_atual)) * 100 as diferenca
from zona_atual
group by all
order by diferenca
```

<BarChart
    data={grupos}
    x=grupo
    y=diferenca
    swapXY=true
    sort=false
    colorPalette={['#d97706']}
    title="Diferença para o preço médio da zona escolhida, em cêntimos por litro"
    yFmt='+0.0;-0.0'
    labels=true
    xAxisTitle=false
    yAxisTitle=false
/>

<DataTable data={grupos} emptySet="pass" emptyMessage="Sem postos nesta zona.">
    <Column id=grupo title="Grupo de marcas" />
    <Column id=postos title="Postos" fmt="#,##0" />
    <Column id=media title="Preço médio (€/L)" fmt='0.000' />
    <Column id=diferenca title="Diferença (cêntimos)" fmt='+0.0;-0.0' />
</DataTable>

Os hiper e supermercados são Intermarché, Pingo Doce, Auchan, E.Leclerc e Recheio. As petrolíferas são Galp, Repsol, BP, Cepsa, Moeve, Shell, Esso e Q8. "Sem marca" são os postos que a DGEG regista como "Genérico".

```sql tipos
select station_type as tipo, count(*) as postos, avg(price) as media
from ${zona}
where is_current
group by all
order by media
```

<DataTable data={tipos} emptySet="pass" emptyMessage="Sem postos nesta zona.">
    <Column id=tipo title="Tipo de posto" />
    <Column id=postos title="Postos" fmt="#,##0" />
    <Column id=media title="Preço médio (€/L)" fmt='0.000' />
</DataTable>

## Por marca

```sql marcas
select brand as marca, count(*) as postos, avg(price) as media, min(price) as minimo, max(price) as maximo
from ${zona}
where is_current
group by all
having count(*) >= 3
order by media
```

<DataTable data={marcas} rows=30 emptySet="pass" emptyMessage="Nenhuma marca com pelo menos 3 postos nesta zona.">
    <Column id=marca title="Marca" />
    <Column id=postos title="Postos" fmt="#,##0" />
    <Column id=media title="Média (€/L)" fmt='0.000' contentType=colorscale colorScale=negative />
    <Column id=minimo title="Mínimo" fmt='0.000' />
    <Column id=maximo title="Máximo" fmt='0.000' />
</DataTable>

Só as marcas com pelo menos 3 postos na zona escolhida.

## Por distrito e por concelho

```sql distritos
select district as distrito, count(*) as postos, avg(price) as media
from combustiveis.postos
where fuel = '${inputs.combustivel.value}' and is_current
group by all
order by media
```

```sql concelhos
select municipality as concelho, district as distrito, count(*) as postos, avg(price) as media, min(price) as minimo
from combustiveis.postos
where fuel = '${inputs.combustivel.value}'
    and is_current
    and district like '${inputs.distrito.value}'
group by all
having count(*) >= 3
order by media
```

<Tabs>
    <Tab label="Concelhos">
        <DataTable data={concelhos} rows=15 search=true emptySet="pass" emptyMessage="Nenhum concelho com pelo menos 3 postos.">
            <Column id=concelho title="Concelho" />
            <Column id=distrito title="Distrito" />
            <Column id=postos title="Postos" fmt="#,##0" />
            <Column id=media title="Média (€/L)" fmt='0.000' contentType=colorscale colorScale=negative />
            <Column id=minimo title="Mais barato" fmt='0.000' />
        </DataTable>
    </Tab>
    <Tab label="Distritos">
        <DataTable data={distritos} rows=20>
            <Column id=distrito title="Distrito" />
            <Column id=postos title="Postos" fmt="#,##0" />
            <Column id=media title="Média (€/L)" fmt='0.000' contentType=colorscale colorScale=negative />
        </DataTable>
    </Tab>
</Tabs>

Os concelhos com pelo menos 3 postos, do mais barato para o mais caro (no distrito escolhido, ou em todo o continente).

## Os mais caros

Os mais baratos estão na tabela por baixo do mapa.

```sql caros
select station_name, brand, municipality, district, price, updated_at
from ${zona}
where is_current
order by price desc, station_name
limit 10
```

<DataTable data={caros} emptySet="pass" emptyMessage="Sem postos nesta zona.">
    <Column id=station_name title="Posto" />
    <Column id=brand title="Marca" />
    <Column id=municipality title="Concelho" />
    <Column id=price title="Preço (€/L)" fmt='0.000' />
    <Column id=updated_at title="Atualizado" fmt='dd/mm/yyyy hh:mm' />
</DataTable>

## Concorrência

Um posto sem concorrentes por perto pode cobrar mais? Para cada posto, conta-se quantos outros há num raio de 5 km (em linha reta) e compara-se o preço com a média do próprio concelho, para não confundir com a diferença entre regiões. Ficam de fora os postos de autoestrada e de hipermercado.

```sql concorrencia_base
select
    brand_segment,
    competitors_5km,
    price,
    case
        when competitors_5km = 0 then '0'
        when competitors_5km <= 2 then '1 a 2'
        when competitors_5km <= 5 then '3 a 5'
        when competitors_5km <= 10 then '6 a 10'
        else '11 ou mais'
    end as concorrentes,
    case
        when competitors_5km = 0 then 1
        when competitors_5km <= 2 then 2
        when competitors_5km <= 5 then 3
        when competitors_5km <= 10 then 4
        else 5
    end as ordem,
    (price - avg(price) over (partition by municipality)) * 100 as vs_concelho
from combustiveis.postos
where fuel = '${inputs.combustivel.value}'
    and is_current
    and station_type = 'Outro'
    and competitors_5km is not null
```

```sql concorrencia
select concorrentes, ordem, count(*) as postos, avg(price) as media, avg(vs_concelho) as vs_concelho
from ${concorrencia_base}
group by all
order by ordem
```

<BarChart
    data={concorrencia}
    x=concorrentes
    y=vs_concelho
    sort=false
    colorPalette={['#64748b']}
    title="Diferença para a média do concelho, em cêntimos por litro, pelo número de concorrentes a 5 km"
    yFmt='+0.0;-0.0'
    labels=true
    xAxisTitle="Concorrentes a 5 km"
    yAxisTitle=false
/>

```sql concorrencia_grupos
select
    brand_segment as grupo,
    avg(vs_concelho) filter (where competitors_5km <= 2) as isolados,
    avg(vs_concelho) filter (where competitors_5km > 2) as com_concorrencia,
    count(*) filter (where competitors_5km <= 2) as postos_isolados
from ${concorrencia_base}
group by all
order by isolados desc
```

<DataTable data={concorrencia_grupos} emptySet="pass">
    <Column id=grupo title="Grupo de marcas" />
    <Column id=postos_isolados title="Postos com 0 a 2 concorrentes" fmt="#,##0" />
    <Column id=isolados title="Diferença para o concelho (cêntimos)" fmt='+0.0;-0.0' />
    <Column id=com_concorrencia title="Com 3 ou mais concorrentes" fmt='+0.0;-0.0' />
</DataTable>

É uma fotografia de um dia: a análise com mais pormenor está em [docs/analises](https://github.com/JoseFerrao20/combustiveis-pt/blob/main/docs/analises/concorrencia-postos.md).

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
