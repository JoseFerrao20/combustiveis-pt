# 0008. O site sem o Evidence

- **Estado:** aceite (substitui a 0002)
- **Data:** 2026-11-04

## Contexto

O painel começou no Evidence (ADR 0002). As páginas que se abrem no telemóvel foram saindo dele, uma a uma, para páginas Svelte leves:
- a página inicial (ADR 0005);
- o resumo e os postos acompanhados (ADR 0006);
- os Açores e a Madeira (ADR 0007).

No Evidence ficaram só as cinco páginas das análises (o índice, os impostos, a previsão, a comparação com a Europa e o método). Por elas, o projeto mantinha:

- **o DuckDB-WASM e o JavaScript do Evidence:** cerca de 12 MB para quem abria uma análise;
- **o Evidence 40.1.8 fixado:** a versão aberta já não recebe novidades, porque a empresa passou para o Evidence Studio;
- **três patches no `node_modules`:** para os números em português, as traduções da interface, a acessibilidade e o service worker;
- **regras próprias:**
  - o `rel="external"` nos links para as páginas leves;
  - as frases dos cartões feitas em SQL, porque o `Value` deixa um espaço a seguir;
  - o `emptySet="pass"` nas tabelas que podem ficar vazias;
  - o `npm run sources`, que fica parado sem acesso a `extensions.duckdb.org`;
- **dois sítios para o aspeto:** o `+layout.svelte` do Evidence e o `base.css` das páginas leves;
- **938 pacotes npm.**

As análises usam pouco do Evidence:
- consultas sobre uma tabela pequena, o boletim em € por litro (uns 10 000 registos);
- três tipos de gráfico: linhas, áreas empilhadas e barras;
- tabelas.

## Decisão

- **As análises passam a páginas Svelte** (`app/analises/…`), como as outras.
  - Leem dois JSON escritos pelo `combustiveis site` (`export_analyses`), a partir dos Parquet que o dbt já exportava:
    - `boletim.json`: Portugal com a divisão do preço em todas as semanas, Espanha e a média da UE, e todos os países na última semana. São uns 90 KB comprimidos.
    - `previsao.json`.
  - As contas que eram SQL nas páginas (erro médio, acerto do sentido, posição de Portugal) passam para JavaScript. São médias e contagens simples.
- **Os gráficos são SVG sem bibliotecas:**
  - o `Grafico.svelte` passa a fazer linhas e áreas empilhadas, e a aceitar séries longas (rótulos por ano e, para os leitores de ecrã, uma tabela com a média de cada ano);
  - o `GraficoBarras.svelte` é novo, para a previsão contra a mudança real.
- **O Evidence sai de vez:**
  - saem as páginas, as fontes SQL, os patches, o `evidence.config.yaml` e o `.evidence/`;
  - o `npm run build` passa a ser só o Vite, com as nove páginas como entradas;
  - o que estava em `static/` (ícones, `og.png`, `sw.js`, redirecionamentos dos endereços antigos, estilo das páginas por concelho) passa para `app/public/`;
  - o Leaflet, que vinha com o Evidence, passa a ser uma dependência direta;
  - o service worker deixa de ter a correção do Evidence para os Parquet no Windows e passa a guardar também as análises.
- **A chave do tema** continua a ser `evidence-theme`, para quem já escolheu um tema não o perder.

## Consequências

- **Nenhuma página descarrega o DuckDB nem Parquet**, e há um teste que o confirma. Todas as páginas abrem sem rede depois de visitadas.
- **O `package-lock.json` passa de 938 pacotes para 92.** O build demora uns 6 segundos e já não depende de `extensions.duckdb.org`.
- **Um só aspeto:** o `base.css` serve todas as páginas, e os números saem em português com o `toLocaleString('pt-PT')`, sem patches.
- **Os gráficos são mais simples do que os do Evidence:** não têm dicas ao passar o rato nem zoom. Os valores estão nas tabelas, e as análises mostram o que mostravam.
- **Sem SQL no browser:** uma análise nova precisa de um JSON novo no `site.py`. O dbt continua a fazer as contas pesadas, e o browser só filtra e soma.
- **A ADR 0002 deixa de valer.** Fica no histórico, como a razão de o projeto ter começado assim.
