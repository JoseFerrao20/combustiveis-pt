# 0006. O resumo e os postos acompanhados fora do Evidence

- **Estado:** aceite
- **Data:** 2026-11-03

## Contexto

Com a página inicial fora do Evidence (ADR 0005), o menu do site passou a ter dois tipos de páginas. A página inicial era leve: uns 200 KB e a tabela em menos de meio segundo. O "Resumo" e os "Postos acompanhados" continuavam no Evidence, e quem tocava nesses links no telemóvel esperava pelos mesmos 12 MB (o DuckDB-WASM, o JavaScript do Evidence e as fontes em Parquet) que a página inicial tinha deixado de descarregar.

As duas páginas usam pouco do Evidence:

- o resumo são médias por grupo de marcas, marca, concelho e distrito, sobre as mesmas linhas que a página inicial já lê (`postos-<combustível>.json`), e um gráfico da evolução;
- os postos acompanhados são uma tabela pequena por posto, um gráfico e um mapa, que já era Leaflet.

As análises (impostos, previsão, comparação com a Europa, método) usam muito mais do Evidence: consultas sobre o histórico desde 2005, gráficos com várias séries e os filtros. Não são as páginas que se abrem no posto.

## Decisão

- **O resumo e os postos acompanhados passam a páginas Svelte próprias**, como a página inicial: `app/resumo/index.html` e `app/acompanhados/index.html`, com os componentes `Resumo.svelte` e `Acompanhados.svelte`. O Vite faz o build das três páginas de uma vez (`rollupOptions.input`), com o código comum em ficheiros partilhados.
- **O resumo calcula as médias no browser**, a partir do JSON do combustível escolhido, que o service worker já guarda para a página inicial. A evolução vem de um JSON pequeno (`dados/evolucao.json`, as médias de cada fotografia no país e por grupo de marcas).
- **Os postos acompanhados leem `dados/acompanhados.json`**, com o histórico de cada posto e os concorrentes a 5 km da última fotografia.
- **Os dois JSON são escritos pelo `combustiveis site`**, a partir dos Parquet que o dbt já exportava (`station_prices_daily`, `tracked_stations_daily`, `tracked_station_competitors`).
- **Os gráficos são SVG simples** (`Grafico.svelte`), sem bibliotecas, com os valores numa tabela para os leitores de ecrã. Os filtros são `<select>` nativos.
- **As análises ficam no Evidence.** O cabeçalho comum marca os links para as páginas fora do Evidence com `rel="external"`, para o Evidence não as tentar abrir como suas (nem as seguir no build).
- **Saem do Evidence** as páginas `resumo.md` e `acompanhados.md` e as fontes que só elas usavam (`postos_diario`, `acompanhados`, `acompanhados_concorrentes`). A fonte `postos` fica reduzida às colunas de que as análises precisam.

## Consequências

- **O resumo e os postos acompanhados ficam tão leves como a página inicial:** uns 60 KB de código (sem comprimir) e os JSON que a página inicial já descarrega, em vez dos 12 MB. Também passam a funcionar sem rede, com o que ficou guardado.
- **As contas do resumo passam do SQL para o JavaScript.** São médias simples sobre as linhas da zona escolhida, mas uma mudança na forma de as calcular tem de ser feita nos dois sítios, se o Evidence também as mostrar.
- **Os gráficos são mais simples do que os do Evidence:** não têm zoom nem dicas ao passar o rato. Chegam para quatro séries de poucas semanas.
- **O Evidence fica só com as análises:** é menos código a depender de uma ferramenta que já não recebe novidades (ADR 0002). Se um dia sair de todo, o caminho é o mesmo.
- **Os testes do Playwright** procuram os filtros pelo nome (`getByRole('combobox', { name: 'Distrito' })`) e confirmam que as duas páginas não descarregam o DuckDB. O axe continua a correr nas duas.
