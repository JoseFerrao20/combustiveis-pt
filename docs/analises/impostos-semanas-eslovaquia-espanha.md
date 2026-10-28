# As semanas soltas de Portugal, a Eslováquia e a Espanha

- **Data:** 2026-10-28
- **Dados:** boletim descarregado a 28/10/2026, até à semana de 19/10/2026
- **Método:** o mesmo das análises de [Portugal](impostos-portugal.md) e da [Lituânia e dos Países Baixos](impostos-lituania-paises-baixos.md). Juntam-se as semanas seguidas com a mesma diferença (`tax_tables_gap`, em euros por 1000 L) e compara-se cada período com as linhas das tabelas e com as semanas à volta.

## Portugal: as 10 semanas que sobravam

Cada semana tem uma explicação, mas não há uma regra que sirva para todas.

| Semana | Produto | Diferença | O que se passa |
|---|---|---|---|
| 23/5/2022 | Gasolina 95 | −12,21 | O ISP desce a 29/5 (domingo); o preço da semana já tem o valor de 29/5 |
| 3/10/2022 | Gasolina 95 | +44,46 | O ISP sobe a 4/10 (terça-feira); o preço já mostra a subida toda |
| 17/4/2023 | Gasóleo | +10,00 | O ISP sobe a 18/4 (terça-feira) |
| 5/6/2023 | Gasolina 95 e gasóleo | +18,36 e +20,00 | Os outros impostos sobem a 6/6 (terça-feira) |
| 25/9/2023 | Gasolina 95 e gasóleo | −10,00 e −20,00 | O ISP desce a 26/9 (terça-feira) |
| 9/9/2024 | Gasolina 95 e gasóleo | +13,77 e +15,00 | Falta na tabela o degrau de 9/9 da taxa de carbono |
| 13/7/2026 | Gasolina 95 | +5,91 | A tabela põe já o ISP da semana seguinte |

- **A mudança a meio da semana (7 das 10).** O preço tem a data de segunda-feira, mas já inclui um imposto que, pela tabela, só começa no dia seguinte (ou no domingo). Em todos estes casos, a diferença é exatamente a mudança do imposto, e na semana seguinte volta a zero. A [análise de Portugal](impostos-portugal.md) já tinha testado usar o imposto do fim da semana em todas as semanas, e o resultado piorava (de 10 para 30 semanas em Portugal). Fica a regra da segunda-feira, e estas semanas passam ao seed, uma a uma.
- **9/9/2024.** A taxa de carbono subiu em dois degraus: a [Portaria n.º 203-A/2024/1](https://info-aduaneiro.portaldasfinancas.gov.pt/pt/legislacao_aduaneira/iec_doclib/Documents/Portaria_203_A_2024_1.pdf), em vigor a 9/9, e outra subida a 16/9. A tabela passa de 26/8 diretamente para o valor de 16/9, e a semana de 9/9 fica com metade da subida (13,77 € na gasolina e 15 € no gasóleo) por explicar.
- **13/7/2026.** A tabela tem o ISP da gasolina com 451,10 € em 13/7 e outra vez em 20/7. Os preços mostram 457,01 € na semana de 13/7, entre o de 6/7 (462,39 €) e o de 20/7: a tabela repetiu o valor da semana seguinte.

## Eslováquia

Havia 714 semanas com diferença (contando cada produto à parte), quase todas num só período.

| Período | Outros impostos, pelos preços | Outros impostos na tabela |
|---|---|---|
| 5/9 a 18/9/2011 | 16,23 | 19,65 |
| 9/1/2017 a 31/1/2024 | 29,65 | 19,65 |
| desde 1/2/2024 | 39,65 | 39,65 |

- **2011:** a tabela regista os novos outros impostos a partir de 1/9, mas os preços só os mostram a partir de 19/9. A tabela tem outra linha com 20/9 (19,651), que é provavelmente a data certa.
- **2017–2024:** os preços mostram mais 10 € de outros impostos desde janeiro de 2017, na gasolina e no gasóleo. A tabela não regista essa subida e, em fevereiro de 2024, passa diretamente de 19,65 € para 39,65 €, o valor que os preços mostram dali em diante. Fica a faltar o degrau intermédio de 29,65 €.

## Espanha

Havia 427 semanas com diferença.

| Período | Produto | Diferença | O que se passa |
|---|---|---|---|
| 2005 a 25/9/2008 | ambos | +6 a +12 | Falta a parte regional do "céntimo sanitario" |
| 20/4/2009 a 28/3/2010 | Gasóleo | −2,29 | A tabela tem 11,65 € de outros impostos em vez de cerca de 9,35 € |
| 21/2/2011, 5/8/2024, 11/11/2024 | ambos ou gasóleo | −34 a +80 | O preço sem impostos dessa semana está errado |
| 23/3, 6/7, 3/8 e 5/10/2026 | ambos | −107 a +187 | Semanas em que os impostos mudam |

- **O "céntimo sanitario" (2005–2008).** O imposto sobre as vendas a retalho de hidrocarbonetos tinha uma parte estatal de 24 € por 1000 L, que já está no ISP da tabela (395,69 € na gasolina e 293,86 € no gasóleo), e uma parte regional, que cada comunidade autónoma decidia. A tabela de outros impostos só começa a 26/9/2008, com cerca de 11,7 € na gasolina e 9,4 € no gasóleo, a média das regiões. Antes disso, a diferença é dessa ordem: 7 € em 2005, quando havia menos regiões a cobrar, e cerca de 12 € de 2006 a 2008, na gasolina. A diferença desaparece na semana em que a tabela começa.
- **Gasóleo, 2009–2010.** A tabela tem 11,65 € de outros impostos durante quase um ano, entre valores de 9,3 e 9,4 € antes e depois. Na gasolina, a linha da mesma data (12,71 €) também é alta, mas a diferença fica abaixo de 1 €.
- **Erros no preço sem impostos.** Em três semanas, o preço com impostos segue a tendência, mas o preço sem impostos salta e volta na semana seguinte (5/8/2024: 772,6 € na gasolina, entre 859,1 € e 841,1 €), ou repete o da semana anterior (11/11/2024, gasóleo). O erro não está nas tabelas de impostos, mas entra no mesmo seed, para o aviso ficar limpo.
- **As mudanças de 2026.** O IVA desce para 10% e o ISP baixa em março de 2026, e os dois voltam a subir em julho. Nas semanas de 23/3 e 6/7, o preço mistura os dois regimes. Em 3/8 e 5/10, as diferenças são frações exatas da mudança do ISP: 4/7 de 50 € (28,57 €) e 5/7 de 150 € (107,14 €). É o que daria uma média dos preços dos sete dias da semana, com o novo valor só em parte deles. Em Portugal, pelo contrário, a mudança aparece inteira. Os países não calculam o preço da semana da mesma maneira.

## O que mudou no projeto

- **Seed `known_tax_table_issues`:** mais 10 linhas de Portugal, 4 da Eslováquia e 15 de Espanha, com a explicação.
- **Aviso `warn_tax_tables_explain_price`:** passa a incluir a Eslováquia e a Espanha, e fica a zero nos cinco países.
