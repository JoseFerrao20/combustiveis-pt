"""Os dados da página inicial do site (``dashboard/app/``), em JSON pequenos.

A página inicial não usa o Evidence: o Evidence descarrega o DuckDB-WASM (uns 8 MB) e todas as
fontes em cada página. Esta lê só o JSON do combustível escolhido, feito aqui a partir dos
Parquet que o dbt exporta para o painel:

- ``postos-<combustível>.json``: um posto por linha (só os preços atualizados nos últimos 30
  dias e com coordenadas, como no mapa do painel), em listas pela ordem de ``COLUMNS``;
- ``resumo.json``: o dia da fotografia, a última atualização recebida, os combustíveis, os
  distritos com os concelhos, e o texto da previsão para segunda-feira.

As horas saem como ``AAAA-MM-DDTHH:MM:SSZ``, como o Evidence as dá ao componente do mapa (a hora
de Lisboa lida como UTC, que o componente mostra com os métodos ``getUTC*``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

# As colunas de cada posto, pela ordem em que saem no JSON (o nome é o que o componente usa).
COLUMNS = (
    "station_id",
    "station_name",
    "brand",
    "station_type",
    "district",
    "municipality",
    "locality",
    "latitude",
    "longitude",
    "price",
    "updated_at",
    "change_since_previous",
    "previous_snapshot_date",
    "last_change_date",
    "recent_history",
)
MINUS = "\u2212"  # o sinal de menos tipográfico, como no painel
# A ordem dos combustíveis no filtro, como no painel.
FUEL_ORDER = ("gasolina_95", "gasolina_98", "gasoleo", "gpl")


@dataclass(frozen=True)
class SiteData:
    snapshot_date: date
    stations: dict[str, int]
    forecast: str | None


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float | Decimal):
        return round(float(value), 6)
    return value


def _cents(value: float) -> str:
    """'▲ +1,5', '▼ -0,4' (com o sinal de menos, U+2212) ou '= 0,0': cêntimos por litro."""
    cents = round(value * 100, 1)
    text = f"{abs(cents):.1f}".replace(".", ",")
    if cents > 0:
        return f"▲ +{text}"
    if cents < 0:
        return f"▼ {MINUS}{text}"
    return "= 0,0"


def forecast_text(rows: list[dict[str, Any]]) -> str | None:
    """O texto da previsão para a última semana prevista, como na faixa do painel."""
    if not rows:
        return None
    week = max(row["target_week"] for row in rows)
    latest = sorted(
        (row for row in rows if row["target_week"] == week),
        key=lambda row: row["product"] == "diesel",
    )
    predicted = ", ".join(
        f"{row['product_name']} {_cents(row['predicted_change'])} cêntimos" for row in latest
    )
    text = (
        f"Previsão para segunda-feira, {week:%d/%m}: {predicted} por litro "
        "(estimativa, sem mudanças do ISP)."
    )
    # Na segunda-feira, a fotografia da DGEG já diz quanto os postos mudaram.
    observed = [row for row in latest if row["dgeg_change"] is not None]
    if observed:
        changes = ", ".join(
            f"{row['product_name']} {_cents(row['dgeg_change'])}" for row in observed
        )
        text += f" Nos postos, a mudança foi de {changes} cêntimos."
    return text


def _write_json(path: Path, content: Any) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, separators=(",", ":")), "utf-8")


def export_site(stations: Path, forecast: Path, target: Path) -> SiteData:
    target.mkdir(parents=True, exist_ok=True)
    db = duckdb.connect()
    snapshot_date, updated_at = db.execute(
        "select max(snapshot_date), max(updated_at) from read_parquet(?)", [str(stations)]
    ).fetchall()[0]
    fuels = db.execute(
        "select distinct fuel, fuel_name from read_parquet(?)", [str(stations)]
    ).fetchall()
    fuels.sort(key=lambda fuel: FUEL_ORDER.index(fuel[0]) if fuel[0] in FUEL_ORDER else 99)
    counts: dict[str, int] = {}
    for fuel, name in fuels:
        rows = db.execute(
            f"""
            select {", ".join(COLUMNS)}
            from read_parquet(?)
            where fuel = ? and is_current and latitude is not null and longitude is not null
            order by price, station_name
            """,  # noqa: S608 (as colunas são as de COLUMNS, não vêm de fora)
            [str(stations), fuel],
        ).fetchall()
        counts[fuel] = len(rows)
        _write_json(
            target / f"postos-{fuel}.json",
            {
                "fuel": fuel,
                "fuel_name": name,
                "snapshot_date": _json_value(snapshot_date),
                "columns": COLUMNS,
                "stations": [[_json_value(value) for value in row] for row in rows],
            },
        )
    districts: dict[str, list[str]] = {}
    for district, municipality in db.execute(
        """
        select distinct district, municipality from read_parquet(?)
        where district is not null and municipality is not null
        order by district, municipality
        """,
        [str(stations)],
    ).fetchall():
        districts.setdefault(district, []).append(municipality)
    cursor = db.execute(
        """
        select target_week, product, product_name, predicted_change, dgeg_change
        from read_parquet(?)
        """,
        [str(forecast)],
    )
    names = [column[0] for column in cursor.description]
    text = forecast_text([dict(zip(names, row, strict=True)) for row in cursor.fetchall()])
    _write_json(
        target / "resumo.json",
        {
            "snapshot_date": _json_value(snapshot_date),
            "updated_at": _json_value(updated_at),
            "fuels": [
                {"fuel": fuel, "name": name, "stations": counts[fuel]} for fuel, name in fuels
            ],
            "districts": districts,
            "forecast": text,
        },
    )
    return SiteData(snapshot_date=snapshot_date, stations=counts, forecast=text)
