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

- **2026-10-27 (sessão cloud do Claude Code):** as tabelas de impostos de Portugal ([análise](docs/analises/impostos-portugal.md)).
  - **Encontrado:** os 826 avisos vinham de três erros nas próprias tabelas.
    - **2008–2011:** a contribuição de serviço rodoviário (64 € na gasolina, 86 € no gasóleo) sai do ISP e não entra na tabela de outros impostos. O total dos preços não muda.
    - **2016–2023:** os outros impostos têm um algarismo a menos (12,15 em vez de 102,15; 14,65 em vez de 140,65; 17,2 em vez de 170,2; 19,41 em vez de 109,41). Daí os patamares de 90, 126 e 153 €.
    - **2025 a março de 2026:** os dois valores do ISP estão trocados entre as linhas de janeiro e de dezembro, por isso as diferenças são simétricas (±16,26 € e ±24,39 €).
  - **Feito:** mais 8 períodos no seed `known_tax_table_issues`. O aviso passa de 826 linhas para 10, todas semanas soltas de 2022 a 2026. Atualizei a página "Como se calcula", o README e a análise anterior.
  - **Testado e posto de lado:** usar o imposto em vigor no fim da semana, em vez do de segunda-feira. Explicaria seis das semanas soltas, mas as diferenças pioram em todos os países (de 6377 para 6831 semanas).
  - **Lição:** um patamar constante é um erro de cópia na fonte. Vale a pena comparar o valor que os preços implicam com o da tabela, algarismo a algarismo.

- **2026-10-28 (sessão cloud do Claude Code):** preços de cada posto em Portugal (DGEG), com uma página nova no painel.
  - **Fonte:** os termos do portal (rodapé) permitem a reutilização, desde que se identifique a DGEG, se mostre a data e hora de atualização de cada preço e não se altere a informação. Não há API documentada, mas a página de pesquisa usa uma API JSON, e um pedido traz os 12 715 preços de 3204 postos em menos de 2 segundos. O dados.gov.pt tem a lista dos postos, sem preços. O José aceitou usar o portal assim ([ADR 0003](docs/adr/0003-precos-dos-postos-dgeg.md), que revê em parte o 0001).
  - **Feito:**
    - `combustiveis dgeg`: leitura validada, como a do boletim (13 testes novos, 35 no total, 98 % de cobertura), com uma amostra real de 30 postos;
    - dbt: `stg_dgeg__station_prices`, `fct_station_prices` (com o grupo da marca e `is_current`), dois modelos para o painel e avisos para preços fora de 0,50–4 € e para a média da DGEG longe do boletim (> 5 %);
    - workflow `dgeg.yml`: uma fotografia por dia no ramo `dados`. O `pages.yml` passa a correr todos os dias e junta o histórico desse ramo;
    - página "Postos em Portugal": mapa dos postos, diferença por grupo de marcas, tipo de posto, marcas, distritos, os 10 mais baratos e os 10 mais caros, e a evolução (quando houver dias suficientes).
  - **Primeiros números** (gasolina 95, 28/10/2026):
    - média de 2,086 € (o boletim dá 2,099 € para 19/10);
    - os hiper e supermercados ficam 9,3 cêntimos abaixo da média e as petrolíferas 2,4 acima;
    - nas autoestradas, 2,154 €;
    - Braga é o distrito mais barato (2,071 €) e Beja o mais caro (2,112 €).
  - **Lições:**
    - a lista que a API devolve diz quantos preços há no total (`Quantidade`): comparar com o número de linhas apanha uma página cortada;
    - há preços que os postos não atualizam há mais de um ano: as médias usam só os dos últimos 30 dias;
    - o gráfico de barras a começar no zero escondia 12 cêntimos de diferença: o painel mostra a diferença para a média.

- **2026-10-28 (sessão cloud do Claude Code):** filtros por distrito e concelho, concorrência entre postos e testes do painel.
  - **Filtros:** a página "Postos em Portugal" tem filtros de distrito e de concelho. O resumo, o mapa (que se ajusta à zona), os grupos de marcas, as marcas e os mais baratos e mais caros passam a ser da zona escolhida. Há também uma tabela de concelhos, com pesquisa.
  - **Concorrência** ([análise](docs/analises/concorrencia-postos.md)):
    - `int_station_neighbours` conta os postos a 2 e 5 km com a fórmula de haversine em SQL, com um teste unitário;
    - os postos sem nenhum concorrente a 5 km são 3,7 cêntimos mais caros na gasolina e 2,8 no gasóleo, e 1,5 a 1,8 acima da média do próprio concelho. Com um ou dois concorrentes, a diferença desaparece;
    - os independentes e os postos sem marca baixam 3 a 4 cêntimos quando há concorrência perto. As petrolíferas e os hiper e supermercados quase não mudam.
  - **Testes do painel:** o Playwright abre as quatro páginas do build (no CI, com a amostra) e confirma que não há erros, que há números e que o filtro de distrito reduz a lista. 8 testes.
  - **Lições:**
    - a extensão espacial do DuckDB não descarrega aqui (o DuckDB não usa o proxy), e a fórmula de haversine em SQL chega para 3000 postos;
    - nos testes unitários do dbt, todas as linhas esperadas têm de ter as mesmas colunas;
    - as listas dos filtros do Evidence só desenham as primeiras opções: o teste escolhe a primeira a seguir a "Todos".

- **2026-10-28 (sessão cloud do Claude Code):** o mapa passa aos mosaicos do OpenStreetMap.
  - **O problema:** com os mosaicos permitidos na sessão, a captura mostrou que os da CARTO, que o Evidence usa por omissão, passaram a exigir uma chave de API. O mapa publicado mostrava "API KEY REQUIRED" em todo o fundo, a qualquer visitante.
  - **Feito:** o `PointMap` usa os mosaicos do OpenStreetMap, com a atribuição "© OpenStreetMap" (o uso é gratuito para sites com pouco tráfego). O endereço vai como texto JavaScript (`basemap={'…{z}/{x}/{y}.png'}`), porque, escrito como atributo, o Svelte lê as chavetas como código e o build falha. A captura da secção de concorrência entrou no README.
  - **Lição:** um serviço externo pode mudar as regras sem aviso. Só se deu por isto por causa da captura; os testes não olham para o fundo do mapa.

- **2026-10-28 (sessão cloud do Claude Code):** captura do mapa dos postos no README, já com o fundo do OpenStreetMap (o domínio dos mosaicos passou a estar nos permitidos da sessão). A captura é do site publicado, com os dados reais.

- **2026-10-28 (sessão cloud do Claude Code):** as últimas semanas de Portugal, a Eslováquia e a Espanha nas tabelas de impostos ([análise](docs/analises/impostos-semanas-eslovaquia-espanha.md)).
  - **Portugal:** as 10 semanas soltas têm explicação. Em 7, o imposto muda entre terça-feira e domingo e o preço com data de segunda-feira já mostra a mudança toda. Em 9/9/2024 falta na tabela um degrau da taxa de carbono (Portaria n.º 203-A/2024/1), e em 13/7/2026 a tabela repete o ISP da semana seguinte.
  - **Eslováquia:** a tabela de outros impostos não regista uma subida de 10 € de 2017 a 2024 (714 semanas), e em 2011 adianta uma mudança em duas semanas.
  - **Espanha:** falta a parte regional do "céntimo sanitario" até setembro de 2008, um valor errado no gasóleo em 2009–2010, três semanas com o preço sem impostos errado e as semanas das mudanças de 2026. Nestas, a diferença é uma fração exata da mudança (4/7 e 5/7), como numa média diária.
  - **Resultado:** o seed `known_tax_table_issues` tem mais 29 linhas, e o aviso `warn_tax_tables_explain_price` cobre os cinco países e está a zero.
  - **Lição:** o boletim não calcula o preço da semana da mesma maneira em todos os países. Em Portugal, a mudança aparece inteira; em Espanha, aos bocados. Uma regra única para a data do imposto nunca deixaria o aviso a zero.

- **2026-10-28 (sessão cloud do Claude Code):** página "Postos acompanhados".
  - **Feito:** o seed `tracked_stations` tem os postos a seguir, pelo id da DGEG: o Auchan Gondomar I (Estrada da Circunvalação, Rio Tinto, ao lado do Parque Nascente) e o Auchan Viseu (Quinta da Alagoa, junto ao Palácio do Gelo). Para cada um, por dia e combustível, `rpt_tracked_stations_daily` tem o preço, a média e o mínimo dos concorrentes a 5 km, a posição entre eles e a média do concelho. `rpt_tracked_station_competitors` lista os concorrentes da última fotografia. A página mostra os números do dia, um mapa com o posto a vermelho, a tabela dos concorrentes e, quando houver mais de 5 dias, a evolução.
  - **Primeiro dia (28/10/2026, gasolina 95):** o Auchan da Circunvalação é o mais barato dos 56 postos a 5 km (1,919 €, empatado com o Auchan de Campanhã), 16 cêntimos abaixo da média. O de Viseu é o 2.º de 20 (1,969 €), atrás do Intermarché de Viseu (1,959 €), e 10 cêntimos abaixo da média.
  - **Amostra dos testes:** o `make_dgeg_sample.py` junta os postos acompanhados e os três mais próximos de cada um, para a página ter dados no CI. Passou de 30 para 37 postos.
  - **Lição:** o `Value` do Evidence deixa um espaço antes da pontuação a seguir; frases com vários valores ficam melhor montadas no SQL.

- **2026-10-28 (sessão cloud do Claude Code):** tabela dos postos por baixo do mapa.
  - **Feito:** na página "Postos em Portugal", o mapa passa a ter por baixo a tabela dos postos que se veem, do mais barato para o mais caro. Ao aproximar ou arrastar o mapa, ou ao filtrar por distrito e concelho, a tabela acompanha. Clicar num posto da tabela aproxima o mapa dele e abre os dados. As cores vão do verde (mais barato) ao vermelho (mais caro), pelos quintis dos preços da zona, e os mais baratos ficam por cima quando os pontos se sobrepõem. A secção "Os mais baratos e os mais caros" fica só com os mais caros.
  - **Decisão:** os mapas do Evidence não dão os limites do mapa à página, por isso o mapa é um componente próprio (`dashboard/components/MapaPostos.svelte`) com o Leaflet, que já vinha com o Evidence. O resto da página continua com os componentes do Evidence.
  - **Lição:** o store de uma consulta do Evidence pode emitir as mesmas linhas mais de uma vez. Se o mapa se reenquadrar a cada emissão, volta atrás depois de o utilizador mexer: o componente só redesenha quando as linhas mudam.

- **2026-10-29 (sessão cloud do Claude Code):** "Perto de mim", caminho até ao posto e partilha do link.
  - **Para quê:** partilhar o painel com a família e os amigos, que o vão abrir no telemóvel.
  - **Feito:**
    - botão "Perto de mim": centra o mapa na localização (depois de a pessoa autorizar; a posição não sai do telemóvel), e a tabela ganha a distância a cada posto;
    - botão "Ir" em cada posto, que abre o caminho no Google Maps;
    - a tabela cabe no telemóvel: abaixo de 640 px, a marca, o concelho e a data passam para debaixo do nome;
    - o mapa já não passa por cima do cabeçalho ao fazer scroll (erro do PR #16);
    - descrição e imagem (`og.png`, com o mapa) para a pré-visualização do link, e um ícone próprio (bomba de combustível com uma seta para baixo) para o separador e para o ecrã principal do telemóvel.
  - **Lições:** a pré-visualização do WhatsApp só aceita a imagem com o endereço completo. O Evidence gera o `manifest.webmanifest` numa rota própria: um ficheiro com o mesmo nome em `static/` parte o build.

- **2026-10-29 (sessão cloud do Claude Code):** uma porta de entrada para a família e os amigos.
  - **Feito:**
    - a página inicial passa a ser a dos postos ("Combustível mais barato"), com o mapa e o "Perto de mim" logo a seguir aos filtros; o resumo do dia vem depois do mapa;
    - as páginas do boletim (impostos, Europa e método) passam para o menu "Análises" (`pages/analises/`); os endereços antigos redirecionam;
    - interface em português: menu, pesquisa e páginas das tabelas, "Feito com o Evidence" e `lang="pt-PT"` (o Chrome deixa de oferecer a tradução), com patches do `patch-package`; o menu deixa de mostrar o SQL ("Show Queries");
    - no telemóvel, o mapa fica com 60 % da altura do ecrã, no máximo, para a tabela aparecer mais cedo.
  - **Lição:** uma página do Evidence sem nenhuma consulta pede um `all-queries.json` que não existe; a página "Análises" tem uma consulta pequena (semanas e postos) por isso.

- **2026-10-29 (sessão cloud do Claude Code):** vigilância do histórico da DGEG.
  - **Porquê:** a DGEG só mostra o preço em vigor, por isso um dia sem fotografia perde-se para sempre. Até aqui, uma recolha parada ou uma resposta incompleta só se via a olhar para o site.
  - **Feito:** `combustiveis verificar-dgeg` (`check.py`, com 7 testes) falha se a última fotografia tiver mais de N dias ou se tiver menos 20 % de postos do que a anterior.
    - O `dgeg.yml` corre-o depois de guardar a fotografia: os dados ficam guardados na mesma, mas o trabalho falha e chega um email.
    - O `pages.yml` tem um trabalho novo, `vigilancia`, que falha se a última fotografia do ramo `dados` tiver mais de 2 dias, por exemplo se o `dgeg.yml` deixar de correr. Fica à parte do build, para o site continuar a ser publicado.
  - **Hoje:** 3153 postos a 29/10, contra 3206 a 28/10 (−1,7 %).

- **2026-10-29 (sessão cloud do Claude Code):** "Desde ontem" e o histórico de cada posto.
  - **Feito:**
    - `int_station_price_changes` (dbt, com um teste unitário) calcula, para cada posto e combustível da última fotografia: o preço da fotografia anterior e a diferença, o de há uma semana, o último dia em que o preço mudou e os preços dos últimos 7 dias em texto. O `rpt_stations_latest` junta estas colunas;
    - na tabela por baixo do mapa, uma coluna "Desde ontem" (▲ vermelho a subir, ▼ verde a descer, em cêntimos; "=" sem mudança), e por cima "Desde ontem, X subiram e Y desceram de preço", contado na parte do mapa que se vê. No telemóvel, a variação vai debaixo do preço;
    - o balão de cada posto mostra os preços dos últimos dias e o dia da última mudança.
  - **Primeiro dia com duas fotografias (29/10, gasolina 95):** 34 postos subiram e 63 desceram; a média mudou −0,07 cêntimos.
  - **Lição:** o Evidence pode entregar uma data vazia como 1/1/1970: o componente trata as datas antes de 2000 como vazias.

- **2026-10-30 (sessão cloud do Claude Code):** previsão do preço de segunda-feira ([análise](docs/analises/previsao-segunda-feira.md), [ADR 0004](docs/adr/0004-previsao-com-cotacoes-do-fred.md)).
  - **Fonte:** o FRED dá de graça, em CSV e sem chave, as cotações diárias da gasolina e do gasóleo em Nova Iorque, o Brent e o câmbio do euro. `combustiveis mercados` descarrega-as e valida-as (11 testes).
  - **Modelo:** a mudança do preço sem impostos à segunda é uma parte da mudança da cotação da semana anterior, mais uma parte da semana antes, com o IVA no fim. Os coeficientes foram ajustados com 2012–2023 e ficam no seed `forecast_coefficients`.
  - **Teste (147 semanas, de 2024 a outubro de 2026):** o erro médio é de 1,2 cêntimos na gasolina e 1,3 no gasóleo, contra 1,9 e 2,7 a dizer "fica igual". Acerta se sobe ou desce em 81 % e 86 % das semanas. Com o Brent, o erro é maior (1,6).
  - **No painel:** a previsão no topo da página inicial e a página "Previsão para segunda-feira" (Análises), com o erro de todas as semanas de teste e os gráficos do previsto contra o real.
  - **Primeira previsão:** para 2/11/2026, gasolina −1,4 cêntimos e gasóleo −6,4, com só 2 dias de cotações dessa semana.
  - **Lições:** os coeficientes ficam num seed, e não no dbt, para o teste ser honesto e o CI funcionar com 5 semanas. Em outubro de 2026, Nova Iorque e a Europa separaram-se na gasolina, e a previsão errou mais; o painel mostra as semanas todas para isso se ver.

- **2026-10-30 (sessão cloud do Claude Code):** a previsão comparada com os postos no próprio dia.
  - **Feito:** `int_dgeg_monday_changes` (com um teste unitário) calcula a mudança média dos postos em cada segunda-feira, a partir das fotografias da DGEG, face à fotografia anterior (até 3 dias antes), só com os preços atualizados nos dois dias. O `fct_price_forecasts` junta-a à previsão (`dgeg_change`).
  - **No painel:** a página da previsão tem uma tabela "Na própria segunda-feira, segundo os postos" (prevista, nos postos, diferença, quantos postos mudaram). Na segunda de manhã, a faixa da página inicial acrescenta "Nos postos, a mudança foi de…".
  - **Ainda vazio:** as fotografias começaram a 28/10, por isso a primeira comparação é a de 2/11/2026. Testado com uma segunda-feira simulada (cópias da fotografia de 29/10, com o gasóleo a −5 cêntimos): a página e a faixa mostram a comparação.

- **2026-10-30 (sessão cloud do Claude Code):** "Compensa ir mais longe?".
  - **Feito:** depois de "Perto de mim", a tabela ganha a coluna "Poupa". É quanto se poupa num depósito em cada posto face ao posto mais perto, já descontando o combustível da ida e volta (a distância em linha reta × 1,3, uma aproximação da estrada). O depósito (50 L) e o consumo (6,5 L/100 km) mudam-se por cima da tabela e ficam guardados no browser. A tabela pode ordenar-se por preço ou por poupança. No telemóvel, a distância passa para debaixo do nome, para a poupança caber.
  - **Exemplo (Lisboa, Avenida da República, gasolina 95):** o PRIO de Arroios, a 1 km, poupa 9,29 € num depósito de 50 L face ao posto mais perto; o MOEVE da Pontinha, a 6,4 km, é mais barato, mas a viagem come parte da diferença (8,78 €).
  - **Decisão:** a distância em linha reta × 1,3 em vez de um serviço de rotas, para não depender de mais um serviço nem enviar a localização a ninguém.

- **2026-10-30 (sessão cloud do Claude Code):** página inicial mais leve.
  - **O problema:** a página inicial descarregava cerca de 16 MB. O Evidence descarrega todas as fontes em todas as páginas (regista cada Parquet sem leitura parcial), e o histórico europeu (2,5 MB) vinha também na página dos postos. Além disso, guarda o resultado de cada consulta, e duas consultas intermédias (`zona` e `concorrencia_base`) levavam todas as colunas dos ~3000 postos (1,8 MB).
  - **Feito:** o `rpt_road_fuel_prices` só leva todas as semanas de Portugal, Espanha e da média da UE, e a última semana dos outros países (o que as páginas mostram), com os valores arredondados ao décimo de milésimo de euro: de 3,6 MB para 215 KB. As duas consultas passaram a escolher só as colunas que usam.
  - **Resultado:** os dados da página inicial passaram de cerca de 4,9 MB para 1,5 MB. O resto (uns 8 MB, comprimidos na transferência) é o código do Evidence e do DuckDB-WASM, que é igual em todas as páginas e fica em cache.
  - **Lição:** no Evidence, o tamanho de uma página depende de todas as fontes do projeto e de todas as consultas da página, mesmo das que só servem de passo intermédio.

- **2026-10-30 (sessão cloud do Claude Code):** README de portfólio.
  - **Feito:** o README abre com o que o site faz para quem abastece (mapa e tabela, "Perto de mim", poupança, "Desde ontem", previsão), com capturas novas:
    - duas vistas no telemóvel, lado a lado;
    - o mapa com a tabela no computador;
    - a previsão;
    - os impostos e a comparação com a Europa, já com o menu "Análises".

    Tem também uma secção de destaques técnicos, a arquitetura com as três fontes e a vigilância, e a lista das quatro decisões (ADR). As capturas antigas que já não se usam saíram, e a dos impostos passou a `painel-impostos.png`.

- **2026-10-31 (sessão cloud do Claude Code):** acessibilidade.
  - **Feito:** `dashboard/tests/a11y.spec.mjs` corre o axe (WCAG 2.2 AA) nas 7 páginas, nos temas claro e escuro (14 testes), e o CI passa a exigi-lo. Os problemas encontrados vinham quase todos dos componentes do Evidence e foram corrigidos com o patch que já traduzia a interface:
    - os filtros diziam-se "combobox" sem `aria-controls`. Abrem um diálogo, por isso passaram a botões normais, com o texto visível como nome;
    - o link do GitHub, só com o ícone, não tinha nome ("Código no GitHub");
    - a caixa de deslocamento das tabelas não se alcançava com o teclado (`tabindex="0"`, com nome);
    - a escala de cores (`colorScale=negative`) ficava abaixo de 4,5:1. Passou a branco → `#fca5a5`, com o texto branco no tema escuro, onde o Evidence escurece a escala;
    - o "Ir" azul no tema escuro tinha contraste 3,8 (passou a `#60a5fa`).

    Também se traduziram "Fullscreen" e os nomes dos botões da paginação.
  - **Lição:** a amostra do CI e os dados reais dão páginas diferentes (tabelas que cabem ou não, máximos da escala de cores). O axe tem de passar nas duas, e duas das falhas só apareciam com a amostra.

## Plano

1. **Com 4 a 6 semanas de fotografias:** quanto tempo as marcas demoram a passar as subidas e descidas do boletim (e se sobem mais depressa do que descem), e se os postos isolados demoram mais a baixar. Nos postos acompanhados, se mudam o preço antes ou depois dos concorrentes.
2. **Ver como a previsão se sai nas próximas semanas** (a primeira comparação com os postos é a 2/11); voltar a correr `scripts/fit_forecast.py` daqui a uns meses.
3. **Captura da página "Postos acompanhados"** para o README, quando o gráfico da evolução já aparecer (mais de 5 dias).
4. **Talvez:** avisar a Comissão dos erros nas tabelas (o resumo está nas análises de `docs/analises/`); outros países no aviso.
