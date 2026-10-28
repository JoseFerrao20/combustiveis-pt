# 0003. Preços de cada posto: fotografias diárias do portal da DGEG

- **Estado:** aceite
- **Data:** 2026-10-28
- **Revê:** em parte, o [ADR 0001](0001-fonte-weekly-oil-bulletin.md), que pôs a DGEG de lado

## Contexto

O Weekly Oil Bulletin dá a média nacional por semana. Para comparar marcas e regiões em Portugal, é preciso o preço de cada posto, e isso só o portal da DGEG ([precoscombustiveis.dgeg.gov.pt](https://precoscombustiveis.dgeg.gov.pt)) tem.

O ADR 0001 pôs a DGEG de lado por não ter uma API documentada nem regras de uso claras. Desde então ficou a saber-se mais:

- **Os termos do portal**, no rodapé: "A informação disponível neste sítio é gratuita, podendo ser utilizada livremente. A reutilização desta informação deverá assegurar a adequada identificação da Direção-Geral de Energia e Geologia enquanto fonte dos dados, bem como a indicação da data-hora da última atualização dos preços e a reprodução fiel de toda a informação."
- **Uma obrigação legal:** os postos têm de comunicar os preços à DGEG antes de os aplicarem (Decreto-Lei n.º 243/2008).
- **A API por trás da página:** a página de pesquisa usa uma API JSON (`/api/PrecoComb/PesquisarPostos`). Um único pedido traz todos os postos e combustíveis, cerca de 12 700 preços de 3200 postos, em menos de 2 segundos.
- **Não há histórico:** o portal só mostra o preço em vigor.
- **O dados.gov.pt** tem a lista de postos da DGEG, mas não os preços.

## Decisão

- **Uma fotografia por dia:** `combustiveis dgeg` faz um pedido a essa API por dia, identificado com o `User-Agent` do projeto, para os combustíveis rodoviários (gasolinas 95 e 98, simples e especiais, gasóleos e GPL). Guarda o resultado tal como veio, num Parquet por dia.
- **O histórico no ramo `dados`:** o workflow `dgeg.yml` guarda as fotografias em `dgeg/AAAA-MM-DD.parquet`, no próprio repositório (o padrão "git scraping"). Cada fotografia tem cerca de 350 KB. Não há serviços nem custos novos, e cada dia fica com o seu commit.
- **A leitura valida a resposta:** confirma o estado, os campos, os combustíveis conhecidos e o número de linhas igual ao total que o portal anuncia. Se algo falhar, lança `DgegFormatError`, como o `parse.py` faz com o boletim.
- **Os termos cumprem-se assim:**
  - o painel diz que a fonte é a DGEG;
  - mostra a data e hora de atualização de cada preço;
  - não altera os preços: as médias excluem os preços com mais de 30 dias, mas a fotografia guarda tudo.

## Consequências

- **O histórico começa no dia da primeira fotografia (28/10/2026).** Não há maneira de recuperar os dias anteriores.
- **A API pode mudar sem aviso.** Nesse caso, a fotografia do dia falha (com email do GitHub) e perde-se esse dia; o painel continua com o histórico que já tem.
- **Só o continente:** os Açores e a Madeira têm preços fixados pelos governos regionais e não estão no portal.
- **Duas fontes que se verificam uma à outra:** a média simples dos postos é comparada com o preço do boletim europeu na mesma semana (aviso acima de 5 %). Não medem o mesmo, porque o boletim pondera pelas vendas, mas não deviam andar longe. No primeiro dia, a gasolina 95 dá 2,086 € na DGEG e 2,099 € no boletim.
