# Diário

- **2026-10-26 (sessão cloud do Claude Code):** início do projeto e ingestão.
  - **Fonte:** a ideia era usar os preços posto a posto da DGEG, mas não há API pública (o acesso é para entidades protocoladas). Passou-se para o Weekly Oil Bulletin da Comissão Europeia, aberto e com 20 anos de histórico ([ADR 0001](docs/adr/0001-fonte-weekly-oil-bulletin.md)).
  - **O ficheiro:** um único `.xlsx` com 7 folhas. As de preços são "largas": uma linha por semana e um bloco de colunas por país (`PT_price_with_tax_euro95`, …), separados por colunas `CTR`, com duas linhas de cabeçalho e notas no fim. As de impostos têm o código do país (`PT_`) só na primeira linha de cada bloco, e uma linha por data de entrada em vigor. Tem 30 "países": os 27, o Reino Unido (até sair) e as médias EU e EUR.
  - **Feito:** `combustiveis ingest` procura o link na página, descarrega o ficheiro (4,4 MB), passa tudo a tabelas longas e escreve `prices.parquet` (287 751 linhas) e `taxes.parquet` (6 972) em 8 segundos, com um manifesto (origem, data, SHA-256, última semana). 15 testes, 96 % de cobertura, com uma amostra do ficheiro real.
  - **Verificado:** em Portugal, (produto + ISP + outros impostos) × 1,23 dá o preço com impostos ao cêntimo (gasolina 95 e gasóleo, semana de 19/10/2026). Vai ser um teste de dados no dbt.
  - **Lições:**
    - o proxy da sessão bloqueava todas as fontes de dados; foi preciso juntar `ec.europa.eu` e `energy.ec.europa.eu` aos domínios permitidos do ambiente;
    - o DuckDB 2.0 tirou o `fetchone()` às relações: o erro explica a alternativa (`fetchall()`).

- **2026-10-26 (sessão cloud do Claude Code):** transformação com o dbt.
  - **Feito:** projeto dbt em `transform/` (dbt-core 1.12 com dbt-duckdb), com as fontes sobre o Parquet da landing. Seeds dos países (com a data de entrada no euro) e dos produtos. Staging com nomes claros. `int_taxes_in_force` junta a cada semana o IVA, o ISP e os outros impostos em vigor com três `ASOF JOIN`. `fct_fuel_prices` decompõe o preço. 30 nós no `dbt build`: seeds, modelos, testes de dados, um teste genérico próprio (`unique_combination`) e três testes unitários. O CI corre o build com a amostra.
  - **Decisão:** a decomposição vem só dos preços e do IVA (IVA = preço − preço/(1+taxa); ISP e outros = o resto), por isso soma sempre o preço. As tabelas de ISP e de outros impostos do boletim servem para verificar: a diferença fica em `tax_tables_gap`, só a partir da entrada no euro (antes, estão em escudos, pesetas, …).
  - **O que os dados mostraram:**
    - em Portugal, as tabelas batem certo ao cêntimo em muitos anos, mas não em 2008–2011, 2016–2018 e 2025: aí a tabela dos "outros impostos" tem valores em falta ou trocados. Ficou como aviso (826 linhas de semana e produto, na gasolina 95 e no gasóleo), não como erro;
    - noutros países a diferença é maior: na Lituânia fica perto de 377 € por 1000 L em 85 % das semanas, o que parece um problema de unidades ou de moeda nas tabelas (por investigar); Países Baixos e Eslováquia também se afastam muito;
    - dois erros de uma semana no próprio boletim, nos fuelóleos: Irlanda a 26/05/2025 e Bélgica a 10/06/2024, com o preço com impostos abaixo do preço sem impostos. Entraram no seed `known_source_errors` com a explicação, e o teste ignora-os;
    - desde 2005, os impostos foram em média 58,8 % do preço da gasolina 95 em Portugal, 50 % no gasóleo e 34,7 % no GPL.
  - **Lições:**
    - os testes unitários do dbt apanharam contas minhas feitas à mão, não o modelo: vale a pena calcular os valores esperados com uma calculadora, não de cabeça;
    - o dbt 1.10+ avisa que `target-path` e `log-path` no `dbt_project.yml` estão obsoletos;
    - no DuckDB, `count(*) weeks` sem `as` dá erro de sintaxe.

## Plano

1. **Painel:** Evidence (SQL e markdown, site estático) no GitHub Pages, sobre o `data/warehouse.duckdb`: a decomposição da última semana, a evolução desde 2005 e a comparação com Espanha e a média da UE.
2. **Agendamento:** GitHub Actions toda a semana (o boletim sai à segunda): ingestão, `dbt build` e o site novo.
3. **Por investigar:** as tabelas de impostos da Lituânia (unidade ou moeda?) e dos Países Baixos.
