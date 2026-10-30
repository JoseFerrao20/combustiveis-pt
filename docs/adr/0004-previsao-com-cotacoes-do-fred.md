# 0004. Previsão de segunda-feira: cotações de Nova Iorque, do FRED

- **Estado:** aceite
- **Data:** 2026-10-30

## Contexto

Em Portugal, os preços dos combustíveis mudam sobretudo à segunda-feira e acompanham as cotações internacionais da semana anterior. Uma estimativa da mudança da próxima segunda é útil para quem abastece. Para isso, são precisas cotações diárias gratuitas, com histórico longo, que se possam descarregar sem chave.

- **As cotações que os vendedores usam** (Platts, noroeste da Europa) são pagas.
- **O FRED** (Federal Reserve Bank of St. Louis) publica de graça, em CSV e sem chave, as cotações diárias da EIA para a gasolina (DGASNYH) e o gasóleo (DDFUELNYH) no porto de Nova Iorque, o Brent (DCOILBRENTEU) e o câmbio do euro (DEXUSEU). Saem com uns dias de atraso: o câmbio só às segundas-feiras.
- **O Weekly Oil Bulletin** dá o preço sem impostos em Portugal, semana a semana, desde 2005: chega para ajustar e testar o modelo.

## Decisão

- **`combustiveis mercados`** descarrega as quatro séries do FRED e escreve `data/landing/mercados.parquet`, com a leitura validada (`MarketFormatError`), como as outras fontes. O `pages.yml` corre-o todos os dias.
- **Um modelo simples e explicável:** a mudança do preço sem impostos à segunda é uma parte da mudança da cotação média da semana anterior, mais uma parte da semana antes dessa (mínimos quadrados sem constante). O IVA junta-se no fim. A previsão não inclui mudanças do ISP.
- **Coeficientes fixos num seed** (`forecast_coefficients`), ajustados com 2012–2023 por `scripts/fit_forecast.py`. O dbt só os aplica. Assim, as semanas de 2024 em diante ficam como teste a sério, e o CI, que só tem 5 semanas do boletim, funciona.
- **Gasolina e gasóleo de Nova Iorque, não o Brent:** no teste, o erro com o Brent é maior (1,6 contra 1,2–1,3 cêntimos).

## Consequências

- O painel mostra a previsão na página inicial e uma página com o erro de todas as semanas de teste, para quem a usa saber quanto confiar nela.
- As cotações de Nova Iorque não são as da Europa: em semanas em que os dois mercados se separam, a previsão erra mais (aconteceu em outubro de 2026, na gasolina).
- Se o FRED mudar o formato, a leitura falha e o site não é atualizado nesse dia, como acontece com o boletim.
- Os coeficientes podem envelhecer: convém voltar a correr `scripts/fit_forecast.py` de vez em quando e ver se o erro do período de teste se mantém.
