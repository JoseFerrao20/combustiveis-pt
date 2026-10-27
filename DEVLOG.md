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

- **2026-10-26 (sessão cloud do Claude Code):** painel com o Evidence.
  - **Feito:** `dashboard/` com três páginas. "Quanto do preço é imposto?" mostra a última semana em Portugal, a divisão em produto, ISP e outros impostos, e IVA, e a evolução desde 2005. "Portugal e a Europa" compara Portugal com Espanha e com a UE, e mostra todos os países na última semana. "Como se calcula" explica o método e as limitações. Tem um filtro por combustível. O dbt exporta `rpt_road_fuel_prices` para Parquet; o CI constrói o painel com a amostra e o `pages.yml` publica-o com os dados reais a cada push na `main`.
  - **Decisões ([ADR 0002](docs/adr/0002-painel-evidence.md)):**
    - o Evidence passou para um serviço com conta (Evidence Studio), e o template deixou de usar a versão open source. Fica a versão open source (40.1.8, MIT), fixada;
    - o painel lê um Parquet e não a base de dados do dbt, porque o Evidence traz o DuckDB 1.4, que não abre ficheiros do DuckDB 2.
  - **Lições:**
    - o `npm install` falhava porque o npm escolhia o TypeScript 7 e o Evidence pede a 5.4.2: ficou fixado;
    - nesta sessão, o `npm run sources` ficava parado sem erro. O DuckDB-WASM tenta descarregar a extensão de Parquet de `extensions.duckdb.org`, e o proxy bloqueia esse domínio. No GitHub Actions funciona; aqui o build ficou por ver;
    - antes de escrever uma frase no painel, confirmar nos dados: "o preço antes de impostos é parecido em toda a UE" era falso (vai de 0,59 a 1,37 € por litro na gasolina 95);
    - uma semana de Espanha (8/4/2013) tem o preço sem impostos mas não o preço com impostos; o modelo do painel deixa de fora as semanas sem os dois.

- **2026-10-26 (sessão cloud do Claude Code):** agendamento.
  - **Feito:** o `pages.yml` passa a correr também à terça e à quinta às 5h53 UTC. O boletim traz os preços de segunda e sai nos dias seguintes; duas execuções por semana apanham-no mesmo com atraso. Opção nova `combustiveis ingest --idade-maxima DIAS`, que falha se a última semana do boletim for mais antiga do que isso; a execução agendada usa 15 dias. 18 testes.
  - **Decisões:**
    - **Avisos pelo próprio GitHub**, sem serviços novos: uma execução agendada que falha manda um email a quem mudou o cron por último. Uma falha na ingestão, no dbt (os testes de dados são erros) ou no build não publica nada, e o site fica com a última versão boa;
    - **Uma fonte parada também é uma falha:** o ficheiro pode continuar a descarregar-se sem ter semanas novas (a Comissão parou, ou o link aponta para um ficheiro antigo), e é isso que a idade máxima apanha. Com 15 dias, uma publicação em falta passa e duas não; no Natal pode falhar uma vez.
  - **Lição:** o GitHub desliga os agendamentos de um repositório público sem commits há 60 dias. Ficou escrito no workflow onde se voltam a ligar.

- **2026-10-26 (sessão cloud do Claude Code):** aspeto do painel.
  - **Feito:**
    - números em português (`2,099 €`, `58,8%`, `1 137`) nos valores, nas tabelas, nos eixos e nas dicas dos gráficos;
    - título "Combustíveis em Portugal", "Início" em vez de "Home" e um link para o repositório (`pages/+layout.svelte`);
    - cores fixas: produto a cinzento, ISP e outros a âmbar, IVA a vermelho; Portugal a verde, Espanha a âmbar e a UE a azul;
    - data da última descarga no fim da página inicial, lida do manifesto da ingestão.
  - **Decisão:** o Evidence formata os números com o `ssf`, que não tem locales. Em vez de formatar os números em texto no SQL (os gráficos ficavam sem eixo numérico), um patch de cinco linhas troca os separadores, só nos números (as datas ficam iguais). Fica em `dashboard/patches/`, aplicado pelo `patch-package`; com as versões fixadas, não muda sem se dar por isso.
  - **Lição:** o `patch-package` ficou parado a criar o patch (corre um `npm i` numa pasta temporária). O patch foi escrito com `git diff --no-index` no mesmo formato, e o `patch-package` aplica-o sem problemas.

- **2026-10-27 (sessão cloud do Claude Code):** painel visto no browser.
  - **Verificado** (site publicado e build local, com o Playwright): números em português, cores, data da descarga, filtro de combustível (gasóleo: 2,175 €, 38,6 % de impostos), modo escuro e telemóvel (390 px, sem scroll horizontal).
  - **Corrigido:**
    - a barra lateral escrevia "Portugal E A Europa" e "Como Se Calcula": o Evidence aplica `capitalize` aos títulos; tirado com CSS no `+layout.svelte`;
    - o caminho de navegação dizia sempre "Home" (está fixo no Evidence): desligado, com três páginas não faz falta;
    - a legenda do gráfico de barras estava em inglês ("Price Without Tax"): o `seriesLabels` não chega às barras empilhadas, por isso as colunas têm nomes em português no SQL;
    - o "27/10/2026 ;" com espaço antes do ponto e vírgula.
  - **Capturas** do painel no README (`docs/images/`).
  - **Lição:** o `npm run sources` não ficava parado por causa do domínio, mas porque o Node não usa o `HTTPS_PROXY`; com `NODE_USE_ENV_PROXY=1` (Node 22.21+) e o certificado do proxy, o build corre nas sessões cloud.

- **2026-10-27 (sessão cloud do Claude Code):** as tabelas de impostos da Lituânia e dos Países Baixos ([análise](docs/analises/impostos-lituania-paises-baixos.md)).
  - **Método:** juntar as semanas seguidas com a mesma diferença e comparar cada período com as linhas das tabelas. As diferenças nunca são ruído: ficam constantes durante meses ou anos e mudam em datas certas.
  - **Lituânia:** as tabelas não acompanharam a passagem ao euro em 2015. A gasolina ficou com uma linha de 2009 até 2024, e o gasóleo com uma de 2013 até 2017. Os preços implicam 434,43 € e 330,17 € por 1000 L, que são exatamente 1500 e 1140 litas à taxa fixa de 3,4528. A decomposição estava certa.
  - **Países Baixos:**
    - os preços incluem desde 2011 uma taxa de 5,9 € (depois 8 €) que a tabela de outros impostos só regista a partir de 2023;
    - em 2008 e 2023, as mudanças do ISP chegam aos preços algumas semanas depois da data da tabela.
  - **Feito:**
    - seed `known_tax_table_issues` (11 períodos, com a explicação) e a coluna `tax_tables_issue` no `fct_fuel_prices`;
    - um teste que impede períodos sobrepostos e um teste unitário novo;
    - o aviso das tabelas passa a cobrir PT, LT e NL fora dos períodos explicados. LT e NL ficam a zero; os 826 avisos são todos de Portugal;
    - uma linha nas limitações do painel.
  - **Pista para Portugal:** em 2008–2011, as diferenças são de 64 € (gasolina) e 86 € (gasóleo), os valores iniciais da contribuição de serviço rodoviário. Falta confirmar.

## Plano

1. **Portugal:** a mesma análise. Os patamares são de 64/86 € em 2008–2011 (contribuição de serviço rodoviário?), 90 € em 2016–2018, 126 € em 2020 e 153 € no gasóleo em 2021–2022. Cada período confirmado entra no seed `known_tax_table_issues`.
2. **Talvez:** guardar o histórico das descargas (cada ficheiro tem um SHA-256 no manifesto) para ver quando a Comissão corrige semanas antigas.
3. **Talvez:** um teste do painel no CI (Playwright sobre o build da amostra).
