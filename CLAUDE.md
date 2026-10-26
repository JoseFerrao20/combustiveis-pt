# combustiveis-pt

Pipeline de dados com os preços semanais dos combustíveis em Portugal e na UE (Weekly Oil Bulletin da Comissão Europeia, desde 2005): ingestão em Python para Parquet (`src/combustiveis/`), depois dbt com DuckDB e um painel com Evidence. Projeto de portfólio de José Ferrão. A escolha da fonte está em `docs/adr/0001-fonte-weekly-oil-bulletin.md`; o histórico e o plano em `DEVLOG.md`.

## Comandos

```bash
uv sync
uv run pytest                                  # cobertura ≥ 90 %
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run combustiveis ingest                     # precisa de acesso a energy.ec.europa.eu
```

## Convenções

- README, DEVLOG, ADR, mensagens de erro e descrições de PR em **português de Portugal**; nomes no código e mensagens de commit em inglês.
- Cada alteração num PR a partir de um ramo, com o CI verde.
- O formato do ficheiro do boletim não está documentado: a leitura (`parse.py`) valida-o e lança `FormatError` em vez de devolver dados errados. Os testes usam `tests/fixtures/oil_bulletin_sample.xlsx`, uma amostra do ficheiro real gerada com `scripts/make_sample.py`: se o formato mudar, gerar outra a partir do ficheiro novo.
- Valores por 1000 L (por tonelada nos fuelóleos). Nas folhas de impostos, uma célula vazia é "sem dados", não zero. O ISP e os outros impostos estão na moeda nacional (escudos antes de 2002).
- O link do ficheiro muda quando a Comissão o substitui: procurar sempre na página (`source.find_history_url`), nunca fixar o endereço.
- `data/` não entra no Git.
- DuckDB 2: as relações já não têm `fetchone()`; usar `fetchall()`.
