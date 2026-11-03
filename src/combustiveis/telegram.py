"""Os avisos de segunda-feira pelo Telegram (``combustiveis telegram``).

Depois da fotografia semanal da DGEG, cada pessoa inscrita recebe uma mensagem com a previsão
para segunda-feira e a mudança nos postos, o preço dos postos que segue (com a mudança na
semana e a posição entre os postos a 5 km) e o posto mais barato do seu distrito.

O site não tem servidor, por isso as inscrições estão num segredo do repositório
(``TELEGRAM_SUBSCRIPTIONS``, uma lista em JSON) e o token do bot noutro
(``TELEGRAM_BOT_TOKEN``). Como criar o bot e inscrever alguém: ``docs/telegram.md``.
"""

from __future__ import annotations

import json
import math
import os
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import duckdb

from .pages import SITE_URL, of_district, tidy
from .site import forecast_summary

API_URL = "https://api.telegram.org"
NEAR_KM = 5.0


class TelegramError(Exception):
    """As inscrições estão mal escritas, ou o Telegram recusou uma mensagem."""


@dataclass(frozen=True)
class Subscription:
    chat_id: int | str
    fuel: str = "gasolina_95"
    stations: list[int] = field(default_factory=list)
    district: str | None = None


def read_subscriptions(text: str | None) -> list[Subscription]:
    """As inscrições, a partir do JSON do segredo (vazio = ninguém inscrito)."""
    if not text or not text.strip():
        return []
    try:
        raw = json.loads(text)
        if not isinstance(raw, list):
            raise TypeError("não é uma lista")
        return [
            Subscription(
                chat_id=item["chat_id"],
                fuel=item.get("combustivel", "gasolina_95"),
                stations=[int(s) for s in item.get("postos", [])],
                district=item.get("distrito"),
            )
            for item in raw
        ]
    except (ValueError, TypeError, KeyError) as exc:
        raise TelegramError(f"TELEGRAM_SUBSCRIPTIONS inválido: {exc}") from exc


def _km(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Distância em linha reta (haversine), como no dbt e no site."""
    rad = math.radians
    h = (
        math.sin(rad(b["latitude"] - a["latitude"]) / 2) ** 2
        + math.cos(rad(a["latitude"]))
        * math.cos(rad(b["latitude"]))
        * math.sin(rad(b["longitude"] - a["longitude"]) / 2) ** 2
    )
    return 2 * 6371 * math.asin(math.sqrt(h))


def _euros(value: float) -> str:
    return f"{value:.3f}".replace(".", ",") + " €"


def _cents(value: float) -> str:
    cents = round(value * 100, 1)
    text = f"{abs(cents):.1f}".replace(".", ",")
    return f"▲ {text} c" if cents > 0 else f"▼ {text} c" if cents < 0 else "= 0,0 c"


def read_data(stations: Path, forecast: Path) -> tuple[date, list[dict[str, Any]], dict[str, Any]]:
    db = duckdb.connect()
    cursor = db.execute(
        """
        select snapshot_date, station_id, station_name, brand, district, municipality, fuel,
            fuel_name, price, latitude, longitude, change_since_previous
        from read_parquet(?)
        where is_current
        """,
        [str(stations)],
    )
    names = [c[0] for c in cursor.description]
    rows = [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
    cursor = db.execute(
        "select target_week, product, product_name, predicted_change, dgeg_change "
        "from read_parquet(?)",
        [str(forecast)],
    )
    names = [c[0] for c in cursor.description]
    summary = forecast_summary([dict(zip(names, r, strict=True)) for r in cursor.fetchall()])
    snapshot = max(row["snapshot_date"] for row in rows)
    return snapshot, rows, summary or {}


def build_message(
    subscription: Subscription,
    snapshot: date,
    rows: list[dict[str, Any]],
    forecast: dict[str, Any],
) -> str:
    """A mensagem de uma pessoa, em texto simples (o Telegram faz os links)."""
    fuel_rows = [r for r in rows if r["fuel"] == subscription.fuel]
    fuel_name = fuel_rows[0]["fuel_name"] if fuel_rows else subscription.fuel
    lines = [f"⛽ Combustíveis em Portugal, fotografia de {snapshot:%d/%m/%Y}"]
    if forecast:
        week = date.fromisoformat(forecast["week"])
        predicted = " · ".join(
            f"{i['name']} {_cents(i['predicted'] / 100)}" for i in forecast["items"]
        )
        lines += ["", f"Previsão para segunda, {week:%d/%m}: {predicted}"]
        observed = [i for i in forecast["items"] if i["observed"] is not None]
        if observed:
            lines.append(
                "Nos postos: "
                + " · ".join(f"{i['name']} {_cents(i['observed'] / 100)}" for i in observed)
            )
    by_id = {r["station_id"]: r for r in fuel_rows}
    if subscription.stations:
        lines += ["", f"Os seus postos ({fuel_name.lower()}):"]
        for station_id in subscription.stations:
            row = by_id.get(station_id)
            if row is None:
                lines.append(f"• posto {station_id}: sem preço atualizado deste combustível")
                continue
            near = [
                o for o in fuel_rows
                if o is not row and o["latitude"] is not None and row["latitude"] is not None
                and _km(row, o) <= NEAR_KM
            ]  # fmt: skip
            position = 1 + sum(1 for o in near if o["price"] < row["price"])
            change = row["change_since_previous"]
            details = [_euros(row["price"])]
            if change is not None:
                details.append(f"na semana {_cents(change)}")
            if near:
                details.append(f"{position}.º de {len(near) + 1} a {NEAR_KM:.0f} km")
            lines.append(f"• {tidy(row['station_name'])}: " + ", ".join(details))
            lines.append(f"  {SITE_URL}?posto={station_id}&combustivel={subscription.fuel}")
    if subscription.district:
        local = [r for r in fuel_rows if r["district"] == subscription.district]
        if local:
            best = min(local, key=lambda r: (r["price"], r["station_name"]))
            lines += [
                "",
                f"Mais barato no {of_district(subscription.district)}: "
                f"{tidy(best['station_name'])} ({best['municipality']}), {_euros(best['price'])}",
            ]
    lines += ["", f"Mapa e todos os postos: {SITE_URL}"]
    return "\n".join(lines)


def _post(url: str, payload: dict[str, Any]) -> bytes:
    request = urllib.request.Request(  # noqa: S310 (o endereço é o da API do Telegram, https)
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 (idem)
        data: bytes = response.read()
    return data


def send(
    token: str,
    messages: list[tuple[Subscription, str]],
    post: Callable[[str, dict[str, Any]], bytes] | None = None,
) -> int:
    """Envia as mensagens; continua se uma falhar, e no fim diz quais falharam."""
    post = post or _post
    failures = []
    for subscription, text in messages:
        try:
            post(
                f"{API_URL}/bot{token}/sendMessage",
                {"chat_id": subscription.chat_id, "text": text, "disable_web_page_preview": True},
            )
        except OSError as exc:  # HTTPError (chat errado, bot bloqueado) e falhas de rede
            failures.append(f"{subscription.chat_id}: {exc}")
    if failures:
        raise TelegramError("Mensagens que falharam:\n- " + "\n- ".join(failures))
    return len(messages)


def subscriptions_from_env() -> list[Subscription]:
    return read_subscriptions(os.environ.get("TELEGRAM_SUBSCRIPTIONS"))
