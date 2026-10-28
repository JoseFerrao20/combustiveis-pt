# As tabelas de impostos de Portugal

- **Data:** 2026-10-27
- **Dados:** boletim descarregado a 27/10/2026, até à semana de 19/10/2026
- **Método:** o mesmo da [análise da Lituânia e dos Países Baixos](impostos-lituania-paises-baixos.md). Juntam-se as semanas seguidas com a mesma diferença (`tax_tables_gap`) e compara-se cada período com as linhas das tabelas.

## A pergunta

Em Portugal, a gasolina 95 e o gasóleo tinham 826 semanas (contando cada produto à parte) em que as tabelas de ISP e de outros impostos do boletim não explicavam o preço, com diferenças acima de 1 € por 1000 L. A divisão do preço no projeto não usa essas tabelas, mas convinha saber se o erro estava nelas.

## O que se viu

As diferenças vêm em patamares constantes, e cada patamar tem uma explicação simples nos números.

### 2008–2011: a contribuição de serviço rodoviário falta na tabela

| | 2007 | 2008–2011 | 2012 | 2013 |
|---|---|---|---|---|
| Gasolina: ISP e outros, pelos preços | 582,95 | 582,95 | 584,42 | 585,27 |
| Gasolina: ISP na tabela | 582,95 | 518,95 | 584,42 | 518,95 |
| Gasolina: outros na tabela | 0 | 0 | 0 | 66,32 |
| Gasóleo: ISP e outros, pelos preços | 364,41 | 364,41 | 366,39 | 367,53 |
| Gasóleo: ISP na tabela | 364,41 | 278,41 | 366,39 | 278,41 |
| Gasóleo: outros na tabela | 0 | 0 | 0 | 89,12 |

Valores em euros por 1000 L.

Em 2008, o total que os preços mostram não muda, mas o ISP na tabela desce 64 € na gasolina e 86 € no gasóleo. São os valores com que a contribuição de serviço rodoviário começou nesse ano (Lei n.º 55/2007). Parte do imposto passou a ser a contribuição, mas a tabela de outros impostos só a mostra a partir de 2013. Em 2012, a tabela volta a juntar tudo no ISP e bate certo.

### 2016–2023: um algarismo a menos nos outros impostos

| Produto | Período | Outros impostos, pelos preços | Outros impostos na tabela |
|---|---|---|---|
| Gasolina 95 | 2016 | 102,15 | 12,15 |
| Gasolina 95 | 2017–2018 | 102,56 | 12,56 |
| Gasolina 95 | 14/2 a 31/12/2020 | 140,65 | 14,65 |
| Gasóleo | 2021–2022 | 170,20 | 17,20 |
| Gasolina 95 | 3/7 a 28/7/2023 | 109,41 | 19,41 |

"Pelos preços" é o ISP e outros impostos que saem dos preços, menos o ISP da tabela. Em todos os casos, o valor da tabela é o certo com um algarismo a menos: 1**0**2,15 → 12,15, 14**0**,65 → 14,65, 17**0**,2 → 17,2, 1**0**9,41 → 19,41. As diferenças de 90, 126 e 153 € vêm só daí. Nos anos à volta, a tabela tem valores da mesma ordem (98,56 em 2015 e 115,94 em 2019, na gasolina).

### 2025 a março de 2026: os dois valores do ISP trocados

| Produto | Período | ISP pelos preços | ISP na tabela |
|---|---|---|---|
| Gasolina 95 | 1/2025 a 11/2025 | 481,26 | 497,52 |
| Gasolina 95 | 12/2025 a 15/3/2026 | 497,52 | 481,26 |
| Gasóleo | 1/2025 a 11/2025 | 337,21 | 361,60 |
| Gasóleo | 12/2025 a 15/3/2026 | 361,60 | 337,21 |

A tabela tem as duas linhas, mas com os valores trocados entre si. Por isso as diferenças são simétricas: −16,26 e +16,26 € na gasolina, −24,39 e +24,39 € no gasóleo.

## O que fica por explicar

Sobram 10 semanas soltas, de 2022 a 2026. Em seis delas, a mudança do imposto tem data entre terça e domingo, e o preço da semana (com data de segunda-feira) já a inclui.

Testou-se usar o imposto em vigor no fim da semana em vez do de segunda-feira. As diferenças acima de 1 € pioraram, de 6377 para 6831 semanas em todos os países, e em Portugal de 10 para 30. Ficou a regra da segunda-feira, e estas semanas ficam no aviso. (Atualização de 28/10/2026: cada uma delas está explicada na [análise das semanas soltas](impostos-semanas-eslovaquia-espanha.md).)

## O que mudou no projeto

- **Seed `known_tax_table_issues`:** mais 8 períodos de Portugal, com a explicação.
- **Aviso `warn_tax_tables_explain_price`:** em Portugal, passa de 826 linhas para 10. Na Lituânia e nos Países Baixos já estava a zero.
