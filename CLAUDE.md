# combustiveis-pt

Pipeline de dados com os preços semanais dos combustíveis em Portugal e na UE (Weekly Oil Bulletin da Comissão Europeia, desde 2005): ingestão em Python para Parquet (`src/combustiveis/`), depois dbt com DuckDB e um painel com Evidence (`dashboard/`, publicado no GitHub Pages pelo `pages.yml`). Projeto de portfólio de José Ferrão. A escolha da fonte está em `docs/adr/0001-fonte-weekly-oil-bulletin.md`; o histórico e o plano em `DEVLOG.md`.

## Comandos

```bash
uv sync --all-groups                           # o grupo transform traz o dbt
uv run pytest                                  # cobertura ≥ 90 %
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run combustiveis ingest                     # precisa de acesso a energy.ec.europa.eu
uv run combustiveis ingest --ficheiro tests/fixtures/oil_bulletin_sample.xlsx   # sem rede
uv run dbt build --project-dir transform --profiles-dir transform   # da raiz; LANDING_DIR, DUCKDB_PATH e EXPORT_PATH mudam os caminhos
cd dashboard && npm ci && npm run sources && npm run build   # painel (Evidence, Node 22), depois do dbt
```

## Convenções

- README, DEVLOG, ADR, mensagens de erro e descrições de PR em **português de Portugal**; nomes no código e mensagens de commit em inglês.
- Cada alteração num PR a partir de um ramo, com o CI verde.
- O formato do ficheiro do boletim não está documentado: a leitura (`parse.py`) valida-o e lança `FormatError` em vez de devolver dados errados. Os testes usam `tests/fixtures/oil_bulletin_sample.xlsx`, uma amostra do ficheiro real gerada com `scripts/make_sample.py`: se o formato mudar, gerar outra a partir do ficheiro novo.
- Valores por 1000 L (por tonelada nos fuelóleos). Nas folhas de impostos, uma célula vazia é "sem dados", não zero. O ISP e os outros impostos estão na moeda nacional (escudos antes de 2002).
- O link do ficheiro muda quando a Comissão o substitui: procurar sempre na página (`source.find_history_url`), nunca fixar o endereço.
- `data/` não entra no Git.
- DuckDB 2: as relações já não têm `fetchone()`; usar `fetchall()`.
- dbt (`transform/`): staging e intermediate são views, marts são tabelas. Testes com a sintaxe `arguments:` do dbt 1.10+. Os testes guardam as linhas que falham (`store_failures`), para se verem no DuckDB. Um erro na fonte não se corrige nos dados: entra no seed `known_source_errors` com a explicação, depois de visto.
- As tabelas de ISP e outros impostos só se comparam com o preço a partir de `countries.euro_since` (antes, estão na moeda nacional). A decomposição (`fct_fuel_prices`) vem dos preços e do IVA; as tabelas só dão o `tax_tables_gap`. Os períodos em que as tabelas estão erradas, já investigados, ficam no seed `known_tax_table_issues` (país, produto, de/até, explicação; sem sobreposições) e aparecem em `tax_tables_issue`; o aviso `warn_tax_tables_explain_price` (PT, LT e NL) ignora-os. Análises em `docs/analises/`.
- DuckDB: um alias de coluna precisa de `as` quando o nome é uma palavra-chave (`count(*) as weeks`).
- Painel (`dashboard/`, ADR 0002): Evidence open source 40.1.8, versões fixadas; já não recebe novidades (a empresa passou para o Evidence Studio). Lê só `data/road_fuel_prices.parquet`, que o dbt exporta (`rpt_road_fuel_prices`), porque o DuckDB do Evidence (1.4) não abre a base de dados do DuckDB 2. Uma coluna nova para o painel entra nesse modelo. O `npm run sources` e o `npm run build` precisam de `extensions.duckdb.org` (o DuckDB-WASM descarrega aí a extensão de Parquet): sem acesso, ficam parados em vez de falhar. Nas sessões cloud, com o proxy, correr com `NODE_USE_ENV_PROXY=1 NODE_EXTRA_CA_CERTS=/root/.ccr/ca-bundle.crt` (o Node não usa o `HTTPS_PROXY` sem isso). O `typescript` fica na 5.4.2, a versão que o Evidence pede.
- O site está em `/combustiveis-pt` (`deployment.basePath`): os links entre páginas passam pela barra lateral do Evidence, não por links escritos à mão.
- Agendamento: o `pages.yml` corre à terça e à quinta (cron em UTC) com `ingest --idade-maxima 15`, que falha se o boletim tiver parado. Uma falha não publica nada: o site fica com a última versão boa.
- Números do painel em português (`2,099 €`, `58,8%`): o `ssf` do Evidence não tem locales, por isso há um patch (`dashboard/patches/`, aplicado pelo `patch-package` no `postinstall`) que troca os separadores na formatação dos números. Se a versão do `@evidence-dev/component-utilities` mudar, o patch tem de ser refeito. As cores das séries estão nas páginas (`seriesColors`, `colorPalette`), e o título e o link do repositório em `pages/+layout.svelte`.
- Ver o painel: depois do build, servir a pasta pai de um link `combustiveis-pt → dashboard/build` (`python3 -m http.server`) e abrir `/combustiveis-pt/`; as páginas são pastas (`comparacao/`). As capturas do README (`docs/images/painel-*.png`, 1280×860, tema claro) tiram-se assim com o Playwright. A barra lateral usa o `title` de cada página; o CSS em `+layout.svelte` tira o `capitalize` do Evidence, e o caminho de navegação está desligado (dizia sempre "Home").
