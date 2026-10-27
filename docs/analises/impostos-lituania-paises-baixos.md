# As tabelas de impostos da Lituânia e dos Países Baixos

- **Data:** 2026-10-27
- **Dados:** boletim descarregado a 27/10/2026, até à semana de 19/10/2026

## A pergunta

O `fct_fuel_prices` calcula o ISP e os outros impostos de cada semana a partir dos preços publicados e da taxa do IVA. As tabelas de impostos do boletim deviam dar o mesmo valor; a diferença fica em `tax_tables_gap`. Na Lituânia, a diferença passava de 1 € por 1000 L em 85 % das semanas, com uma mediana perto de 377 €; nos Países Baixos, em 59 %. O cálculo está errado, ou estão as tabelas?

## Como se viu

Para a gasolina 95 e o gasóleo, juntaram-se as semanas seguidas com a mesma diferença. Depois, cada período foi comparado com as linhas das tabelas (`stg_bulletin__taxes`).

A diferença nunca é ruído: fica constante durante meses ou anos e muda em datas certas. Isso aponta para valores fixos e desatualizados nas tabelas, não para os preços. Em cada período, o valor que vem dos preços é uma taxa redonda, enquanto o da tabela não bate certo com ela.

## Lituânia

A Lituânia passou ao euro a 1/1/2015, mas as tabelas não acompanharam a mudança.

| Produto | Período | Tabela (ISP + outros) | Preços | O que se passa |
|---|---|---|---|---|
| Gasolina 95 | 2015–2019 | 1014,23 + 47 | 434,43 | A linha do ISP é de 2009, de antes do euro. 434,43 € são exatamente 1500 litas à taxa fixa de 3,4528. |
| Gasolina 95 | 2020–2024 | 1014,23 + 47 | 466,00 | A tabela continua sem mudanças, mas o valor implícito sobe para 466 €. |
| Gasolina 95 | desde 2025 | 466 + 47, depois 466 + 96 | 513,00, depois 562,00 | A tabela bate certo. |
| Gasóleo | 2015–2017 | 653,45 + 53,6 | 330,17 | A linha do ISP é de 2013. 330,17 € são 1140 litas à taxa fixa. |
| Gasóleo | 2018–2019 | 347 + 53,6 | 347,00 | O ISP bate certo, mas os outros impostos (com data de 2008) não estão no preço. |
| Gasóleo | 2020 a 1/2024 | 347 + 53,6 | 372,00 | O ISP implícito sobe sem mudança na tabela. |
| Gasóleo | 22/1/2024 a 2024 | 347 + 53,6 | 410,00 | O ISP implícito volta a subir. |
| Gasóleo | 2025 | 466 + 53,6 | 519,60 | A tabela bate certo. |
| Gasóleo | 1/2026 a 4/2026 | 466 + 53,6 | 553,60 | O ISP de 500 € já está no preço, mas a tabela só o regista em 22/6/2026. |

Valores em euros por 1000 L.

**Conclusão:** a decomposição está certa. As taxas que saem dos preços batem ao cêntimo com as taxas lituanas em litas convertidas à taxa fixa do euro. Foi a tabela que ficou com valores antigos.

## Países Baixos

| Produto | Período | Diferença | O que se passa |
|---|---|---|---|
| Gasolina 95 | 1/2008 a 8/2008 | −29,4 | A tabela tem a subida do ISP a 1/1/2008, mas os preços só a incluem a partir de setembro. |
| Gasóleo | 7/2008 | −31,3 | O mesmo: a subida de 1/7/2008 só chega aos preços em agosto. |
| Os dois | 2011 a 3/2013 | +5,9 | Os preços têm uma taxa de 5,9 € que a tabela de outros impostos não tem. |
| Os dois | 4/2013 a 2022 | +8,0 | A mesma taxa, já em 8 €. |
| Os dois | 1/2023 a 6/2023 | +2,1 | A tabela regista 5,9 €, mas os preços já incluem 8 €. |
| Gasolina 95 | 3/7 a 24/7/2023 | −138,4 | O fim da descida do ISP de 2022 (1/7/2023) só chega aos preços a 31/7. |

**Conclusão:** a tabela de outros impostos só começa em 2023, mas os valores que lá estão (5,9 e 8 €) são os que os preços mostram desde 2011. Provavelmente é a taxa das reservas estratégicas de petróleo, mas o boletim não diz o que é. Nas mudanças do ISP, os preços chegam algumas semanas depois da data da tabela.

## O que mudou no projeto

- **Novo seed `known_tax_table_issues`:** cada período acima, com a explicação. Os dados não se corrigem: a explicação vai para a coluna `fct_fuel_prices.tax_tables_issue`.
- **O aviso `warn_tax_tables_explain_price`:** passa a cobrir Portugal, a Lituânia e os Países Baixos, e ignora os períodos explicados. Hoje, todas as diferenças da Lituânia (1021 semanas e produto) e dos Países Baixos (1283) têm explicação. Os avisos que ficam (826) são todos de Portugal.
- **Um novo período por explicar** aparece no aviso; quando for visto, entra no seed.

## Por ver

- **Portugal**, com o mesmo método: as diferenças também são constantes por períodos.
  - Em 2008–2011 são de 64 € na gasolina e 86 € no gasóleo, os valores com que a contribuição de serviço rodoviário começou em 2008. Isso sugere que a tabela de outros impostos não a tinha nesses anos, mas falta confirmar.
  - Há outros patamares por explicar: 90 € na gasolina em 2016–2018, 126 € em 2020 e 153 € no gasóleo em 2021–2022.
- **Outros países com muitas diferenças:** Eslováquia (40 % das semanas) e Espanha (20 %).
