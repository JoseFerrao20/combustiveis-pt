# Manutenção

O site atualiza-se sozinho. Esta página diz o que corre e quando, que avisos podem chegar por email e o que fazer em cada caso. Não é preciso fazer nada enquanto não chegar um aviso.

## O que corre sozinho

| Workflow | Quando (hora de Lisboa, aprox.) | O que faz |
|---|---|---|
| `dgeg.yml` (Fotografia DGEG) | segundas, 5h40 | tira a fotografia dos preços de todos os postos do continente e guarda-a no ramo `dados` |
| `pages.yml` (Painel) | todos os dias às 5h50, a seguir à fotografia e a cada push na `main` | descarrega o boletim europeu e as cotações, corre o dbt, publica o site e verifica-o; à segunda, envia os avisos pelo Telegram |
| `ilhas.yml` (Açores e Madeira) | todos os dias, 19h20 | lê os despachos novos dos preços máximos e guarda-os no ramo `dados` |
| `ci.yml` (CI) | em cada PR | testes em Python, dbt e Playwright, com amostras fixas das fontes |

O ramo `dados` guarda o histórico que as fontes não guardam: as fotografias da DGEG (`dgeg/`) e os preços máximos das ilhas (`ilhas/`). Nunca se reescreve. Uma execução que falhe não apaga nada.

## Avisos por email e o que fazer

O GitHub manda um email quando um workflow falha. O passo que falhou diz porquê.

### "O boletim não tem uma semana dos últimos 15 dias" (`pages.yml`, passo `ingest`)

A Comissão Europeia não publicou o Weekly Oil Bulletin, ou mudou o link. O site continua com a última versão boa.

1. Ver se a [página do boletim](https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en) tem semanas recentes. Se não tiver, é esperar. Há pausas no verão e no Natal.
2. Se tiver e o passo falhar com `SourceError`, o link mudou de forma: ajustar `source.find_history_url`.
3. Se falhar com `FormatError`, o ficheiro mudou de formato: gerar outra amostra com `scripts/make_sample.py` a partir do ficheiro novo, ajustar `parse.py` e correr os testes.

### "A última fotografia da DGEG é de …" ou "menos 20 % de postos" (`dgeg.yml` ou trabalho `vigilancia`)

A fotografia de segunda-feira falhou ou veio incompleta. A DGEG só mostra o preço em vigor, por isso uma semana perdida não se recupera.

1. Correr outra vez, no mesmo dia: Actions → Fotografia DGEG → Run workflow.
2. Se falhar com `DgegFormatError`, a API do portal mudou: ver a resposta em `precoscombustiveis.dgeg.gov.pt`, ajustar `dgeg.py` e gerar outra amostra (`scripts/make_dgeg_sample.py`).

### "Faltam preços das regiões autónomas" ou um `IslandFormatError` (`ilhas.yml`)

O despacho da semana (Madeira) ou do mês (Açores) não saiu ou não se conseguiu ler. O que se leu antes fica guardado, e a leitura para antes do despacho com o problema.

1. Ver no passo "Despachos novos" o endereço do PDF que falhou e abri-lo.
2. Se a redação mudou (outra frase, o € noutro sítio), ajustar a expressão regular em `ilhas.py` (`_MADEIRA_*` ou `_ACORES_*`). Acrescentar um teste em `tests/test_ilhas.py` com o texto novo (`make_pdf`) e fazer um PR. A execução seguinte volta a esse despacho.
3. Se o despacho ainda não saiu (feriados), a vigilância volta a falhar no dia seguinte. Não é preciso fazer nada.

### "O site publicado tem problemas" (`pages.yml`, trabalho `verificar`)

O site foi publicado, mas falta alguma coisa. O email tem a lista dos problemas. O mais comum é uma fotografia da DGEG antiga, que é o caso acima.

### Os avisos do Telegram não chegaram

O passo "Avisos pelo Telegram" não faz falhar o site (`continue-on-error`): ver o registo dele no `pages.yml` de segunda-feira. As causas mais prováveis são um token revogado ou uma inscrição com o `chat_id` errado ([docs/telegram.md](telegram.md)).

## Sem aviso, mas a ter em conta

- **O GitHub desliga os agendamentos** de um repositório público sem atividade durante 60 dias. Se o site deixar de se atualizar sem nenhum email, voltar a ligá-los: Actions → cada workflow → "Enable workflow".
- **A previsão de segunda-feira** usa coeficientes ajustados com 2012–2023. Uma vez por ano, ou se o erro médio na página da previsão subir muito, correr `uv run python scripts/fit_forecast.py` com os dados reais e, se o erro descer, `--gravar` num PR.
- **Versões:**
  - o Evidence (40.1.8) já não recebe novidades e fica fixado, com os patches em `dashboard/patches/`;
  - o `@playwright/test` (1.64.1) segue a imagem dos runners do GitHub: quando o CI falhar ao instalar o Chromium, subir a versão;
  - o resto atualiza-se quando for preciso, num PR com o CI verde.
- **Capturas do README:** quando o aspeto mudar, gerar outra vez as das páginas leves com o painel a correr e os dados reais: `node scripts/capturas.cjs http://localhost:8765/combustiveis-pt/`, na pasta `dashboard/`.

## Limites conhecidos

- **Continente:** os preços dos postos são uma fotografia por semana, à segunda-feira, e não o preço de cada dia.
- **Ilhas:** há o preço máximo de cada região, e não o de cada posto. Os Açores começam em fevereiro de 2025.
- **Previsão:** é uma estimativa, sem as mudanças do ISP. O erro de cada semana está no site.
