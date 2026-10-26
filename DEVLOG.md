# Diário

- **2026-10-26 (sessão cloud do Claude Code):** início do projeto e ingestão.
  - **Fonte:** a ideia era usar os preços posto a posto da DGEG, mas não há API pública (o acesso é para entidades protocoladas). Passou-se para o Weekly Oil Bulletin da Comissão Europeia, aberto e com 20 anos de histórico ([ADR 0001](docs/adr/0001-fonte-weekly-oil-bulletin.md)).
  - **O ficheiro:** um único `.xlsx` com 7 folhas. As de preços são "largas": uma linha por semana e um bloco de colunas por país (`PT_price_with_tax_euro95`, …), separados por colunas `CTR`, com duas linhas de cabeçalho e notas no fim. As de impostos têm o código do país (`PT_`) só na primeira linha de cada bloco, e uma linha por data de entrada em vigor. Tem 30 "países": os 27, o Reino Unido (até sair) e as médias EU e EUR.
  - **Feito:** `combustiveis ingest` procura o link na página, descarrega o ficheiro (4,4 MB), passa tudo a tabelas longas e escreve `prices.parquet` (287 751 linhas) e `taxes.parquet` (6 972) em 8 segundos, com um manifesto (origem, data, SHA-256, última semana). 15 testes, 96 % de cobertura, com uma amostra do ficheiro real.
  - **Verificado:** em Portugal, (produto + ISP + outros impostos) × 1,23 dá o preço com impostos ao cêntimo (gasolina 95 e gasóleo, semana de 19/10/2026). Vai ser um teste de dados no dbt.
  - **Lições:**
    - o proxy da sessão bloqueava todas as fontes de dados; foi preciso juntar `ec.europa.eu` e `energy.ec.europa.eu` aos domínios permitidos do ambiente;
    - o DuckDB 2.0 tirou o `fetchone()` às relações: o erro explica a alternativa (`fetchall()`).

## Plano

1. **Transformação (dbt com DuckDB):** fontes sobre o Parquet; staging com os nomes dos produtos e países; um modelo com o imposto em vigor em cada semana (o ISP muda quase todas as semanas desde 2022); a decomposição do preço (produto, ISP, outros, IVA); testes (unicidade, valores aceites, preço com impostos ≥ sem impostos, decomposição bate certo em Portugal).
2. **Painel:** Evidence (SQL e markdown, site estático) no GitHub Pages, com a decomposição, a evolução desde 2005 e a comparação com Espanha e a UE.
3. **Agendamento:** GitHub Actions toda a semana (o boletim sai à segunda): ingestão, `dbt build` e o site novo.
