# Previsão do preço de segunda-feira

- **Data:** 2026-10-30
- **Dados:** boletim até à semana de 19/10/2026; FRED até 27/10/2026
- **Decisão:** [ADR 0004](../adr/0004-previsao-com-cotacoes-do-fred.md)

## A pergunta

Dá para prever quanto muda o preço da gasolina e do gasóleo em Portugal na próxima segunda-feira, só com dados gratuitos?

## O método

- **A mudança a prever:** o preço sem impostos em Portugal (Weekly Oil Bulletin) de uma segunda-feira para a seguinte, em euros por 1000 L.
- **As variáveis:** a mudança da cotação média da gasolina (DGASNYH) ou do gasóleo (DDFUELNYH) em Nova Iorque, em euros por 1000 L com o câmbio do dia. Primeiro entre a semana anterior e a antes dela, depois a mesma diferença uma semana antes.
- **O ajuste:** mínimos quadrados sem constante, com as semanas de 2012 a 2023 (577 semanas).
- **O teste:** as 147 semanas de 2024 a outubro de 2026, que o ajuste não viu. O erro está em cêntimos por litro, com IVA.

## O que se viu

| | Coeficientes | Erro médio | Erro a dizer "fica igual" | Acerta se sobe ou desce |
|---|---|---|---|---|
| Gasolina 95 (Nova Iorque) | 0,54 e 0,28 | 1,2 | 1,9 | 81 % |
| Gasóleo (Nova Iorque) | 0,52 e 0,04 | 1,3 | 2,7 | 86 % |
| Gasolina 95 (Brent) | 0,72 e 0,31 | 1,6 | 1,9 | 74 % |
| Gasóleo (Brent) | 0,77 e 0,26 | 1,6 | 2,7 | 78 % |

- **A previsão ajuda:** o erro fica em 1,2 a 1,3 cêntimos, contra 1,9 a 2,7 sem previsão. Acerta se o preço sobe ou desce em mais de 4 de cada 5 semanas.
- **O refinado é melhor do que o Brent:** o preço da gasolina e do gasóleo já refinados acompanha melhor os preços em Portugal do que o petróleo.
- **Só cerca de metade passa ao preço sem impostos:** os coeficientes andam pelos 0,5. A cotação de Nova Iorque é uma aproximação da europeia, que os vendedores usam, e por isso a relação fica mais fraca do que um para um.
- **Contra o preço com impostos que o boletim publicou** (ISP incluído), o erro médio é de 1,1 cêntimos nos dois combustíveis. As mudanças do ISP de 2026 compensaram parte das subidas e das descidas.
- **Outubro de 2026 foi difícil para a gasolina:** em 12/10, a previsão era −4,5 cêntimos, e a mudança sem impostos foi de +4,0. Nas semanas em que Nova Iorque e a Europa se separam, a previsão erra mais. O painel mostra as semanas todas, para se ver isso.

## O que mudou no projeto

- `combustiveis mercados` (`markets.py`, com testes), o seed `forecast_coefficients` e `scripts/fit_forecast.py`.
- Modelos `int_market_weeks`, `fct_price_forecasts` (com um teste unitário) e `rpt_price_forecast`.
- No painel: a previsão no topo da página inicial e a página "Previsão para segunda-feira", em Análises.
