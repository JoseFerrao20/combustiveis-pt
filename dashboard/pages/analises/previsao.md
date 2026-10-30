---
title: Previsão para segunda-feira
sidebar_position: 2
description: Quanto deve mudar o preço da gasolina e do gasóleo na próxima segunda-feira, e como a previsão se tem saído.
og:
  image: https://joseferrao20.github.io/combustiveis-pt/og.png
---

Em Portugal, os preços mudam sobretudo à segunda-feira e acompanham os mercados internacionais da semana anterior. Com as cotações da gasolina e do gasóleo no porto de Nova Iorque e o câmbio do euro, dá para estimar quanto deve mudar o preço na próxima segunda. É uma estimativa: os postos decidem os preços, e o Governo pode mudar o ISP.

```sql proxima
select *, predicted_change * 100 as centimos
from combustiveis.previsao
where target_week = (select max(target_week) from combustiveis.previsao)
order by product = 'diesel'
```

```sql proxima_texto
select
    'Segunda-feira, ' || strftime(max(target_week), '%d/%m/%Y') || ', com as cotações até '
        || strftime(max(last_market_day), '%d/%m') || ' (' || cast(min(market_days_last_week) as integer)
        || ' de 5 dias da semana).' as texto
from ${proxima}
```

## <Value data={proxima_texto} column=texto />

```sql proxima_gasoleo
select * from ${proxima} where product = 'diesel'
```

```sql proxima_gasolina
select * from ${proxima} where product = 'euro95'
```

<BigValue data={proxima_gasolina} value=centimos title="Gasolina 95" fmt='+0.0 "cêntimos";-0.0 "cêntimos"' />
<BigValue data={proxima_gasoleo} value=centimos title="Gasóleo" fmt='+0.0 "cêntimos";-0.0 "cêntimos"' />

Mudança prevista no preço por litro, com IVA, sem contar com uma eventual mudança do ISP. Com menos de 5 dias de cotações, a previsão ainda pode mudar até ao fim da semana.

## Como se tem saído

```sql historico
select
    target_week as semana,
    product_name as combustivel,
    product,
    predicted_change as prevista,
    actual_change as real,
    abs(predicted_change - actual_change) as erro
from combustiveis.previsao
where is_known
order by semana
```

```sql acerto
select
    product_name as combustivel,
    count(*) as semanas,
    avg(abs(predicted_change - actual_change)) * 100 as erro_medio,
    avg(abs(actual_change)) * 100 as erro_sem_previsao,
    avg(case when sign(predicted_change) = sign(actual_change) then 1.0 else 0.0 end)
        filter (where actual_change <> 0) as acerta_sentido,
    min(target_week) as desde
from combustiveis.previsao
where is_known
group by all
order by combustivel desc
```

<DataTable data={acerto} emptySet="pass" emptyMessage="Ainda não há semanas para comparar.">
    <Column id=combustivel title="Combustível" />
    <Column id=semanas title="Semanas" />
    <Column id=erro_medio title="Erro médio (cêntimos)" fmt='0.0' />
    <Column id=erro_sem_previsao title='Erro a dizer "fica igual"' fmt='0.0' />
    <Column id=acerta_sentido title="Acerta se sobe ou desce" fmt=pct0 />
</DataTable>

A previsão compara-se com a mudança do preço com impostos que o boletim europeu publicou para Portugal, ISP incluído. Os coeficientes foram ajustados com as semanas de 2012 a 2023; as semanas acima são todas posteriores, por isso o erro é o de uma previsão a sério.

```sql grafico
select semana, combustivel, 'Prevista' as serie, prevista * 100 as centimos from ${historico}
where semana >= (select max(semana) from ${historico}) - interval 26 week
union all
select semana, combustivel, 'Real', real * 100 from ${historico}
where semana >= (select max(semana) from ${historico}) - interval 26 week
order by semana
```

```sql grafico_gasolina
select * from ${grafico} where combustivel = 'Gasolina 95'
```

```sql grafico_gasoleo
select * from ${grafico} where combustivel = 'Gasóleo'
```

<BarChart
    data={grafico_gasolina}
    x=semana
    y=centimos
    series=serie
    type=grouped
    seriesColors={{'Prevista': '#94a3b8', 'Real': '#d97706'}}
    title="Gasolina 95: mudança à segunda-feira, em cêntimos por litro (últimos 6 meses)"
    yFmt='+0.0;-0.0'
    xFmt='dd/mm'
    xAxisTitle=false
    yAxisTitle=false
    emptySet="pass"
/>

<BarChart
    data={grafico_gasoleo}
    x=semana
    y=centimos
    series=serie
    type=grouped
    seriesColors={{'Prevista': '#94a3b8', 'Real': '#b45309'}}
    title="Gasóleo: mudança à segunda-feira, em cêntimos por litro (últimos 6 meses)"
    yFmt='+0.0;-0.0'
    xFmt='dd/mm'
    xAxisTitle=false
    yAxisTitle=false
    emptySet="pass"
/>

## Como se calcula

Para cada combustível, a mudança do preço sem impostos à segunda-feira é uma parte da mudança da cotação média em Nova Iorque na semana anterior, mais uma parte da mudança da semana antes dessa. As duas partes ajustam-se com os dados de 2012 a 2023 (mínimos quadrados), e o IVA junta-se no fim. As cotações estão em dólares por galão e passam a euros por 1000 L com o câmbio do dia.

- **Porque não o Brent:** testou-se também com o preço do petróleo, e o erro é maior. A gasolina e o gasóleo já refinados acompanham melhor os preços em Portugal.
- **Limites:** os preços de Portugal seguem as cotações do noroeste da Europa, e não as de Nova Iorque, que são as que estão disponíveis de graça; o FRED publica-as com uns dias de atraso; e o ISP pode mudar à segunda-feira, o que a previsão não tenta adivinhar.

<p class="text-sm text-base-content-muted">Fontes: cotações e câmbio do FRED, Federal Reserve Bank of St. Louis (U.S. Energy Information Administration e Federal Reserve); preços de Portugal do Weekly Oil Bulletin da Comissão Europeia. O código está em <a href="https://github.com/JoseFerrao20/combustiveis-pt">JoseFerrao20/combustiveis-pt</a>.</p>
