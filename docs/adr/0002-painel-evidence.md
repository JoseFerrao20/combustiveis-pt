# 0002. Painel: Evidence open source, com os dados em Parquet

- **Estado:** aceite
- **Data:** 2026-10-26

## Contexto

O painel tem de ser um site estático (GitHub Pages, sem servidor nem custos), escrito em SQL e markdown, sobre os dados do dbt.

O [Evidence](https://github.com/evidence-dev/evidence) faz isto: páginas em markdown com consultas SQL, gráficos e filtros, e um site estático em que as consultas correm no browser, com o DuckDB-WASM. Mas, em 2026, a empresa passou para o "Evidence Studio", um serviço com conta, e o template do projeto deixou de usar a versão open source. A versão open source continua no npm (`@evidence-dev/evidence` 40.1.8, de fevereiro de 2026), com licença MIT, e funciona, mas já não recebe novidades.

Há ainda outra limitação: o Evidence traz o DuckDB 1.4, que não abre uma base de dados criada pelo DuckDB 2 (o do dbt).

## Decisão

- Usar o Evidence open source, com as versões fixadas (`dashboard/package.json` e `package-lock.json`).
- O dbt exporta a tabela do painel para Parquet (`rpt_road_fuel_prices`, materializada como `external`). O Evidence lê esse ficheiro com uma base de dados em memória. O Parquet é lido pelas duas versões do DuckDB e deixa o painel separado do formato da base de dados do dbt.

## Consequências

- O painel só depende de um ficheiro Parquet com colunas conhecidas. Se for preciso trocar de ferramenta (o Observable Framework, por exemplo), as páginas mudam, mas o dbt não.
- Sem atualizações do Evidence, as dependências vão ficando antigas. Como o site é estático e não tem dados pessoais, o risco é baixo. O `typescript` está fixado na 5.4.2, a versão que o Evidence pede, porque o npm escolhia a 7 e a instalação falhava.
- O `npm run sources` precisa de acesso a `extensions.duckdb.org`: o DuckDB-WASM descarrega aí a extensão de Parquet. Sem acesso, o comando fica parado em vez de falhar. Atrás de um proxy, o Node só o usa com `NODE_USE_ENV_PROXY=1`.
