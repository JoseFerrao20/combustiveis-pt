# Avisos de segunda-feira pelo Telegram

Todas as segundas-feiras, depois da fotografia da DGEG (`dgeg.yml`), o `pages.yml` manda a cada pessoa inscrita uma mensagem como esta:

```
⛽ Combustíveis em Portugal, fotografia de 09/11/2026

Previsão para segunda, 09/11: Gasolina 95 ▼ 1,4 c · Gasóleo ▼ 6,4 c
Nos postos: Gasolina 95 ▼ 1,9 c · Gasóleo ▲ 1,3 c

Os seus postos (gasóleo):
• Auchan Gondomar II - Campanhã: 1,899 €, na semana ▼ 2,0 c, 1.º de 50 a 5 km
  https://joseferrao20.github.io/combustiveis-pt/?posto=67347&combustivel=gasoleo

Mais barato no distrito do Porto: Auchan Vila do Conde (Vila do Conde), 1,899 €

Mapa e todos os postos: https://joseferrao20.github.io/combustiveis-pt/
```

O site não tem servidor, por isso não há inscrição pelo próprio bot: as inscrições ficam num segredo do repositório, e acrescentar alguém é editar esse segredo.

## 1. Criar o bot (uma vez)

1. No Telegram, abrir uma conversa com o [@BotFather](https://t.me/BotFather) e enviar `/newbot`.
2. Escolher o nome (por exemplo, "Combustíveis em Portugal") e o nome de utilizador, que tem de acabar em `bot` (por exemplo, `combustiveis_pt_bot`).
3. O BotFather responde com o **token** (algo como `123456789:AA…`). Não o partilhar: quem o tiver manda mensagens em nome do bot.
4. No GitHub, em **Settings → Secrets and variables → Actions → New repository secret**, criar o segredo `TELEGRAM_BOT_TOKEN` com esse token.

## 2. Inscrever uma pessoa (ou um grupo)

1. A pessoa abre a conversa com o bot e carrega em **Iniciar** (o Telegram não deixa um bot escrever a quem nunca falou com ele). Para um grupo da família, junta-se o bot ao grupo.
2. Para saber o número da conversa (`chat_id`), abrir no browser `https://api.telegram.org/bot<TOKEN>/getUpdates`, com o token no lugar de `<TOKEN>`, e procurar `"chat":{"id": …}`. Numa conversa com uma pessoa é um número positivo; num grupo, negativo.
3. O id de cada posto está no link de "Partilhar" do site (`?posto=67347`).
4. Criar (ou editar) o segredo `TELEGRAM_SUBSCRIPTIONS` com uma lista em JSON, uma entrada por conversa:

```json
[
  {"chat_id": 123456789, "combustivel": "gasoleo", "postos": [67347, 67262], "distrito": "Porto"},
  {"chat_id": -100987654321, "combustivel": "gasolina_95", "distrito": "Viseu"}
]
```

- `combustivel`: `gasolina_95` (por omissão), `gasolina_98`, `gasoleo` ou `gpl`;
- `postos`: os ids dos postos que a pessoa segue (pode ficar vazio);
- `distrito`: para a linha "mais barato no distrito" (pode faltar).

## Experimentar

Sem enviar nada, com os dados locais (depois do dbt):

```bash
TELEGRAM_SUBSCRIPTIONS='[{"chat_id": 1, "combustivel": "gasoleo", "postos": [67347], "distrito": "Porto"}]' \
  uv run combustiveis telegram
```

Para mandar já uma mensagem de teste, correr à mão a "Fotografia DGEG" (Actions → Fotografia DGEG → Run workflow): o "Painel" corre a seguir e envia os avisos.

Sem os dois segredos, o passo não envia nada e o site é publicado na mesma. Se o Telegram recusar uma mensagem (por exemplo, a pessoa bloqueou o bot), as outras seguem e o passo fica a vermelho no Actions, mas o site é publicado.
