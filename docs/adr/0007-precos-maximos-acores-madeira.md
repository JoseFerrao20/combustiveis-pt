# 0007. Os preços máximos dos Açores e da Madeira, lidos dos jornais oficiais

- **Estado:** aceite
- **Data:** 2026-11-04

## Contexto

O portal da DGEG (ADR 0003) só tem os postos de Portugal continental. Nas regiões autónomas, o preço da gasolina 95 e do gasóleo não é livre: o governo regional fixa um **preço máximo de venda ao público**, e os postos vendem, quase todos, a esse preço. Para quem vive nas ilhas, esse é o número que interessa, e o site não o mostrava.

Os preços máximos só saem em PDF, nos jornais oficiais:

- **Madeira:** todas as semanas, num despacho conjunto da II série do JORAM, quase sempre num suplemento de sexta-feira, em vigor na segunda. A página de cada ano do JORAM lista os PDFs.
- **Açores:** todos os meses, num despacho normativo da I série do Jornal Oficial, em vigor no dia 1. O site do Jornal Oficial tem uma verificação anti-robôs (Cloudflare) em todas as páginas, menos nos PDFs. Os números da I série têm endereços sequenciais (`I-2026-139-S0.pdf`), e cada um traz o índice e os atos completos.

Não há outra fonte com o histórico. Os sites de notícias e os comparadores repetem os valores, mas sem a garantia da fonte nem o histórico completo.

## Decisão

- **Ler os despachos em PDF** com o pypdfium2 (`ilhas.py`), que não precisa de programas instalados no sistema, ao contrário do `pdftotext`.
  - A leitura procura frases que se repetem há anos, como "homologação dos preços máximos de venda ao público dos combustíveis" ou "fixar os seguintes preços máximos … dos combustíveis líquidos", e lê os preços e a data de entrada em vigor.
  - Valida o que encontra: um preço fora de 0,80 a 3,50 € ou uma data que não bate certo com a publicação é um erro (`IslandFormatError`). É melhor parar do que guardar um valor errado, como no `parse.py` e no `dgeg.py`.
- **Seguir só o que a fonte publica, sem contornar a proteção:**
  - Madeira: a lista de cada ano, e só os PDFs novos. Primeiro lêem-se as duas páginas do sumário, porque alguns números têm dezenas de MB, e o resto só quando o sumário tem o despacho.
  - Açores: os números seguintes ao último lido, até ao primeiro que não existe.
  - Há uma pausa de um segundo entre pedidos.
- **Um workflow diário** (`ilhas.yml`) guarda o histórico no ramo `dados` (`ilhas/precos.csv`, com o ponto onde parou em `ilhas/estado.json`), como as fotografias da DGEG.
  - Um despacho que não se consegue ler faz parar a leitura antes dele, depois de guardar o que leu até aí. Corrigida a leitura, a execução seguinte volta a esse despacho.
  - `verificar-ilhas` falha, com email, se faltar o preço da semana na Madeira ou o do mês nos Açores.
- **O dbt junta o preço médio dos postos do continente** em cada período (`rpt_island_prices`), para comparar. O site tem a página "Açores e Madeira" (`app/ilhas/`) e o CSV nos dados abertos.

## Consequências

- **O site passa a servir as ilhas,** com um histórico desde 2025, até agora inexistente num só sítio: 95 despachos da Madeira e 22 dos Açores na primeira leitura.
- **Não há mapa nem preço por posto nas ilhas:** é um preço máximo por região, o mesmo em todos os postos de todas as ilhas.
- **A leitura é frágil por natureza:** se os despachos mudarem de redação, a leitura falha, e a vigilância avisa. A correção é ajustar uma expressão regular e acrescentar um teste com o texto novo.
- **A primeira leitura é pesada:** cerca de 1 GB de PDFs da Madeira, porque alguns números têm dezenas de MB. As leituras seguintes são só os números novos de cada dia.
- **Os Açores começam em fevereiro de 2025:** o despacho de janeiro de 2025 saiu em dezembro de 2024, antes do início da leitura.
