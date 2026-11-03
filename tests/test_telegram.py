import io
import json
import urllib.error
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import pytest
from test_site import FORECAST

from combustiveis import __main__ as cli
from combustiveis import telegram
from combustiveis.telegram import (
    Subscription,
    TelegramError,
    build_message,
    read_subscriptions,
    send,
)

SNAPSHOT = date(2026, 11, 2)
# Três postos com gasóleo no Porto (dois a menos de 5 km um do outro) e um em Lisboa.
STATIONS = """
select * from (values
    (date '2026-11-02', 1, 'AUCHAN GONDOMAR', 'AUCHAN', 'Porto', 'Gondomar', 'gasoleo', 'Gasóleo',
     1.899, 41.174, -8.566, -0.02, true),
    (date '2026-11-02', 2, 'Galp Rio Tinto', 'GALP', 'Porto', 'Gondomar', 'gasoleo', 'Gasóleo',
     1.959, 41.180, -8.560, null, true),
    (date '2026-11-02', 3, 'BP Lisboa', 'BP', 'Lisboa', 'Lisboa', 'gasoleo', 'Gasóleo',
     1.799, 38.72, -9.14, 0.01, true),
    -- Sem o preço atualizado: não conta.
    (date '2026-11-02', 4, 'Velho', 'BP', 'Porto', 'Porto', 'gasoleo', 'Gasóleo',
     1.5, 41.175, -8.565, null, false)
) as t(snapshot_date, station_id, station_name, brand, district, municipality, fuel, fuel_name,
       price, latitude, longitude, change_since_previous, is_current)
"""


@pytest.fixture
def sources(tmp_path: Path) -> tuple[Path, Path]:
    stations, forecast = tmp_path / "postos.parquet", tmp_path / "previsao.parquet"
    duckdb.sql(f"copy ({STATIONS}) to '{stations}' (format parquet)")
    duckdb.sql(f"copy ({FORECAST}) to '{forecast}' (format parquet)")
    return stations, forecast


def test_read_subscriptions() -> None:
    assert read_subscriptions(None) == []
    assert read_subscriptions("  ") == []
    [one] = read_subscriptions(
        '[{"chat_id": 42, "combustivel": "gasoleo", "postos": ["1", 2], "distrito": "Porto"}]'
    )
    assert one == Subscription(chat_id=42, fuel="gasoleo", stations=[1, 2], district="Porto")
    assert read_subscriptions('[{"chat_id": 7}]')[0].fuel == "gasolina_95"
    for bad in ("{", '{"chat_id": 1}', '[{"postos": [1]}]'):
        with pytest.raises(TelegramError, match="TELEGRAM_SUBSCRIPTIONS inválido"):
            read_subscriptions(bad)


def test_the_message(sources: tuple[Path, Path]) -> None:
    snapshot, rows, forecast = telegram.read_data(*sources)
    assert snapshot == SNAPSHOT
    subscription = Subscription(chat_id=1, fuel="gasoleo", stations=[1, 99], district="Porto")
    text = build_message(subscription, snapshot, rows, forecast)
    assert text.startswith("⛽ Combustíveis em Portugal, fotografia de 02/11/2026")
    assert "Previsão para segunda, 02/11: Gasolina 95 ▼ 1,4 c · Gasóleo ▼ 6,4 c" in text
    assert "Nos postos: Gasóleo ▼ 5,1 c" in text
    assert "• Auchan Gondomar: 1,899 €, na semana ▼ 2,0 c, 1.º de 2 a 5 km" in text
    assert "?posto=1&combustivel=gasoleo" in text
    assert "• posto 99: sem preço atualizado deste combustível" in text
    # O posto sem o preço atualizado (mais barato) não conta.
    assert "Mais barato no distrito do Porto: Auchan Gondomar (Gondomar), 1,899 €" in text
    # Sem postos nem distrito, só a previsão e o link.
    short = build_message(Subscription(chat_id=1), snapshot, rows, {})
    assert "Os seus postos" not in short
    assert short.endswith("Mapa e todos os postos: https://joseferrao20.github.io/combustiveis-pt/")


def test_send_reports_every_failure() -> None:
    sent: list[tuple[str, dict[str, Any]]] = []

    def post(url: str, payload: dict[str, Any]) -> bytes:
        if payload["chat_id"] == 2:
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, io.BytesIO())  # type: ignore[arg-type]
        sent.append((url, payload))
        return b"{}"

    messages = [(Subscription(chat_id=1), "olá"), (Subscription(chat_id=2), "olá")]
    with pytest.raises(TelegramError, match="2: HTTP Error 403"):
        send("TOKEN", messages, post)
    assert sent == [
        (
            "https://api.telegram.org/botTOKEN/sendMessage",
            {"chat_id": 1, "text": "olá", "disable_web_page_preview": True},
        )
    ]
    assert send("TOKEN", messages[:1], post) == 1


def test_command_line(
    sources: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stations, forecast = sources
    args = ["telegram", "--postos", str(stations), "--previsao", str(forecast)]
    monkeypatch.delenv("TELEGRAM_SUBSCRIPTIONS", raising=False)
    assert cli.main(args) == 0
    assert "Ninguém inscrito" in capsys.readouterr().out

    monkeypatch.setenv("TELEGRAM_SUBSCRIPTIONS", json.dumps([{"chat_id": 5, "postos": [1]}]))
    assert cli.main(args) == 0
    assert "--- para 5" in capsys.readouterr().out

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    assert cli.main([*args, "--enviar"]) == 0
    assert "Sem TELEGRAM_BOT_TOKEN" in capsys.readouterr().out

    sent: list[dict[str, Any]] = []
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "TOKEN")

    def fake_post(url: str, payload: dict[str, Any]) -> bytes:
        sent.append(payload)
        return b"{}"

    monkeypatch.setattr(telegram, "_post", fake_post)
    assert cli.main([*args, "--enviar"]) == 0
    assert "Avisos enviados: 1" in capsys.readouterr().out
    assert sent[0]["chat_id"] == 5

    monkeypatch.setenv("TELEGRAM_SUBSCRIPTIONS", "não é JSON")
    assert cli.main(args) == 1
    assert "erro: TELEGRAM_SUBSCRIPTIONS inválido" in capsys.readouterr().err
