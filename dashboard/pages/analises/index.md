---
title: Análises
sidebar_position: 2
description: Quanto do preço dos combustíveis são impostos, Portugal comparado com a Europa, e como se fazem as contas.
og:
  image: https://joseferrao20.github.io/combustiveis-pt/og.png
---

Para quem quer ir além do posto mais barato. As páginas estão no menu:

- **Quanto do preço é imposto?** A parte do preço da gasolina e do gasóleo que é ISP e IVA, semana a semana desde 2005 (Weekly Oil Bulletin da Comissão Europeia).
- **Previsão para segunda-feira:** quanto deve mudar o preço na próxima segunda, a partir dos mercados internacionais, e como a previsão se tem saído.
- **Portugal e a Europa:** o preço em Portugal comparado com Espanha e com a média da União Europeia.
- **Como se calcula:** de onde vêm os dados, as contas e os limites.

```sql dados
select
    (select count(distinct week) from combustiveis.precos) as semanas,
    (select min(week) from combustiveis.precos) as desde,
    (select count(distinct station_id) from combustiveis.postos) as postos
```

Os dados:

- boletim europeu: <Value data={dados} column=semanas /> semanas, desde <Value data={dados} column=desde fmt="dd/mm/yyyy" />
- postos em Portugal: <Value data={dados} column=postos fmt="#,##0" />
