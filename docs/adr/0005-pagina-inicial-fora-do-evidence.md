# 0005. A página inicial fora do Evidence, e a funcionar com pouca rede

- **Estado:** aceite
- **Data:** 2026-11-02

## Contexto

A página inicial (o mapa e a tabela dos postos) é a que a família e os amigos abrem no telemóvel, muitas vezes já no posto e com pouca rede. Com o Evidence (ADR 0002), descarregava cerca de 12 MB comprimidos antes de mostrar a tabela:

- 7,8 MB eram o DuckDB-WASM, de que o Evidence precisa para refazer as consultas quando se muda um filtro;
- 2,7 MB eram JavaScript do Evidence (incluindo os gráficos, que a página quase não usa);
- 0,4 MB eram as fontes (os Parquet), descarregadas inteiras em todas as páginas;
- 0,4 MB era a letra Inter.

O mapa já era um componente próprio (`MapaPostos.svelte`). Os filtros, a procura, os favoritos e a poupança já corriam no browser, sobre as linhas da consulta. Do Evidence, a página só usava os filtros, a consulta e as tabelas de resumo.

## Decisão

- **A página inicial é uma página Svelte própria** (`dashboard/app/`, com o Vite e o Svelte 4 que já vêm com o Evidence), que usa o mesmo `MapaPostos.svelte`. Lê um JSON do combustível escolhido (cerca de 130 KB comprimidos), escrito pelo `combustiveis site` a partir dos Parquet que o dbt exporta. Ao todo, são cerca de 200 KB, e a tabela aparece sem esperar pelo DuckDB.
- **O build junta as duas:** `npm run build` faz o build do Evidence e, depois, o da página inicial, que escreve o `index.html` da raiz e a pasta `inicio/`. O `pages/index.md` do Evidence fica só para os links das páginas do Evidence ("Início"): ao abrir, pede a página ao servidor.
- **As tabelas de resumo** (médias por grupo de marcas, marca, distrito e concelho, concorrência e evolução) ficam no Evidence, na página "Resumo e estatísticas" (`pages/resumo.md`). Usam consultas que o Evidence faz bem e que não são urgentes no telemóvel.
- **Pouca rede:** um service worker (`static/sw.js`) guarda a página inicial, os seus ficheiros e os JSON dos preços. Pede sempre à rede primeiro. Se a rede falhar, ou não responder em 4 segundos, usa o que guardou e a página diz que são os preços guardados. O Evidence registava o seu próprio service worker no mesmo âmbito (uma correção para os Parquet no Windows). Um patch passa a registar o `sw.js`, que inclui essa correção, para os dois não se substituírem um ao outro.

## Consequências

- **A página inicial fica cerca de 60 vezes mais leve:** abre a tabela em menos de meio segundo, em vez de esperar pelos 12 MB.
- **Dois sítios para o aspeto:** a página inicial tem o seu CSS (`app/src/base.css`), com as cores dos temas do Evidence e as poucas classes do Tailwind que o componente usa. Uma mudança de cor no Evidence não chega lá sozinha.
- **O componente tem de funcionar fora do Evidence:** só pode contar com um store de linhas (`data`), e não com os componentes nem com as consultas do Evidence.
- **Sem rede, o mapa fica sem fundo:** os mosaicos do OpenStreetMap não se guardam. Vêm de outro domínio, e o browser reserva vários MB por cada resposta opaca. Os postos, a tabela e os favoritos funcionam na mesma.
- **Os testes do Playwright** cobrem as duas: a página inicial (filtros, procura, favoritos, sem rede, sem DuckDB) e as páginas do Evidence, com o axe nas duas.
