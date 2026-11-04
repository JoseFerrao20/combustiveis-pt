"""Os dados das páginas do site (``dashboard/app/``), em JSON pequenos (ADR 0005, 0006 e 0008).

Cada página lê só o JSON de que precisa, feito aqui a partir dos Parquet que o dbt exporta:

- ``postos-<combustível>.json``: um posto por linha (só os preços atualizados nos últimos 30
  dias e com coordenadas, como no mapa do painel), em listas pela ordem de ``COLUMNS``;
- ``resumo.json``: o dia da fotografia, a última atualização recebida, os combustíveis, os
  distritos com os concelhos, o número de postos e o texto da previsão para segunda-feira;
- ``evolucao.json`` e ``acompanhados.json``: o resumo e os postos acompanhados;
- ``ilhas.json``: os preços máximos dos Açores e da Madeira;
- ``boletim.json`` e ``previsao.json``: as análises.

As horas saem como ``AAAA-MM-DDTHH:MM:SSZ`` (a hora de Lisboa escrita como UTC, que as páginas
mostram com os métodos ``getUTC*``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from .pages import write_pages

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
    "brand_segment",
    "competitors_5km",
)
MINUS = "\u2212"  # o sinal de menos tipográfico, como no painel
# A ordem dos combustíveis no filtro, como no painel.
FUEL_ORDER = ("gasolina_95", "gasolina_98", "gasoleo", "gpl")


@dataclass(frozen=True)
class SiteData:
    snapshot_date: date
    stations: dict[str, int]
    forecast: str | None
    pages: int = 0


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


def _latest_forecast(rows: list[dict[str, Any]]) -> tuple[date, list[dict[str, Any]]]:
    """A última semana prevista e as suas linhas, com a gasolina antes do gasóleo."""
    week = max(row["target_week"] for row in rows)
    latest = sorted(
        (row for row in rows if row["target_week"] == week),
        key=lambda row: row["product"] == "diesel",
    )
    return week, latest


def forecast_summary(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """A previsão em números, para a linha curta da página inicial (cêntimos por litro)."""
    if not rows:
        return None
    week, latest = _latest_forecast(rows)
    return {
        "week": week.isoformat(),
        "items": [
            {
                "name": row["product_name"],
                "predicted": round(float(row["predicted_change"]) * 100, 1),
                "observed": None
                if row["dgeg_change"] is None
                else round(float(row["dgeg_change"]) * 100, 1),
            }
            for row in latest
        ],
    }


def forecast_text(rows: list[dict[str, Any]]) -> str | None:
    """O texto da previsão para a última semana prevista, como na faixa do painel."""
    if not rows:
        return None
    week, latest = _latest_forecast(rows)
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


def _rows(db: duckdb.DuckDBPyConnection, query: str, params: list[Any]) -> list[dict[str, Any]]:
    cursor = db.execute(query, params)
    names = [column[0] for column in cursor.description]
    return [
        {name: _json_value(value) for name, value in zip(names, row, strict=True)}
        for row in cursor.fetchall()
    ]


def export_history(daily: Path, target: Path) -> int:
    """``evolucao.json``: o preço médio em cada fotografia, no país e por grupo de marcas."""
    db = duckdb.connect()
    rows = _rows(
        db,
        """
        select snapshot_date, fuel, label, round(avg_price, 4) as avg_price, stations
        from read_parquet(?)
        where dimension in ('Portugal', 'Grupo de marcas')
        order by fuel, snapshot_date, dimension <> 'Portugal', label
        """,
        [str(daily)],
    )
    _write_json(target / "evolucao.json", {"rows": rows})
    return len(rows)


def export_tracked(tracked: Path, competitors: Path, target: Path) -> int:
    """``acompanhados.json``: cada posto acompanhado, fotografia a fotografia, e os concorrentes
    a 5 km na última fotografia (só os preços atualizados)."""
    db = duckdb.connect()
    history = _rows(
        db,
        """
        select snapshot_date, station_id, label, location, station_name, brand, municipality,
            latitude, longitude, fuel, fuel_name, price, updated_at, competitors,
            round(competitors_avg_price, 4) as competitors_avg_price, competitors_min_price,
            rank_5km, round(municipality_avg_price, 4) as municipality_avg_price
        from read_parquet(?)
        where price is not null
        order by label, fuel, snapshot_date
        """,
        [str(tracked)],
    )
    rivals = _rows(
        db,
        """
        select station_id, competitor_id, station_name, brand, latitude, longitude,
            round(distance_km, 2) as distance_km, fuel, price, updated_at
        from read_parquet(?)
        where is_current and snapshot_date = (select max(snapshot_date) from read_parquet(?))
        order by station_id, fuel, price, distance_km
        """,
        [str(competitors), str(competitors)],
    )
    _write_json(target / "acompanhados.json", {"history": history, "competitors": rivals})
    return len(history)


def _write_json(path: Path, content: Any) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, separators=(",", ":")), "utf-8")


def export_site(
    stations: Path, forecast: Path, target: Path, pages: Path | None = None
) -> SiteData:
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
    forecast_rows = [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
    text = forecast_text(forecast_rows)
    _write_json(
        target / "resumo.json",
        {
            "snapshot_date": _json_value(snapshot_date),
            "updated_at": _json_value(updated_at),
            "fuels": [
                {"fuel": fuel, "name": name, "stations": counts[fuel]} for fuel, name in fuels
            ],
            "districts": districts,
            "stations_total": db.execute(
                "select count(distinct station_id) from read_parquet(?)", [str(stations)]
            ).fetchall()[0][0],
            "forecast": text,
            "forecast_summary": forecast_summary(forecast_rows),
        },
    )
    written = 0 if pages is None else write_pages(stations, pages, snapshot_date)
    return SiteData(snapshot_date=snapshot_date, stations=counts, forecast=text, pages=written)


def export_islands(islands: Path, target: Path) -> int:
    """``ilhas.json``: os preços máximos dos Açores e da Madeira (ADR 0007), com o período em
    vigor e o preço médio dos postos do continente nesse período."""
    db = duckdb.connect()
    rows = _rows(
        db,
        """
        select region, region_name, fuel, fuel_name, valid_from, valid_to, price, act,
            published, source_url, continent_snapshot,
            round(continent_avg_price, 4) as continent_avg_price, continent_stations
        from read_parquet(?)
        order by region, fuel, valid_from
        """,
        [str(islands)],
    )
    _write_json(target / "ilhas.json", {"rows": rows})
    return len(rows)


# As colunas dos JSON das análises (listas pela ordem destas colunas, para ficarem pequenos).
PORTUGAL_COLUMNS = (
    "week",
    "product",
    "price",
    "price_without_tax",
    "excise_and_other_taxes",
    "vat_amount",
    "taxes_total",
    "tax_share",
)
COUNTRY_COLUMNS = (
    "country_code",
    "country",
    "price",
    "price_without_tax",
    "taxes_total",
    "tax_share",
)


def _table(db: duckdb.DuckDBPyConnection, query: str, params: list[Any]) -> list[list[Any]]:
    return [[_json_value(value) for value in row] for row in db.execute(query, params).fetchall()]


def export_analyses(prices: Path, forecast: Path, manifest: Path | None, target: Path) -> int:
    """Os JSON das páginas das análises (ADR 0008), a partir do que o dbt exporta:

    - ``boletim.json``: o Weekly Oil Bulletin em € por litro. Portugal com a divisão do preço
      em todas as semanas; Espanha e a média da UE com o preço; e todos os países na última
      semana de cada combustível. Com a data da última descarga do boletim (``manifest.json``).
    - ``previsao.json``: a previsão de segunda-feira de todas as semanas desde 2024.

    Devolve o número de semanas do boletim.
    """
    db = duckdb.connect()
    source = "read_parquet(?)"
    products = _table(
        db,
        f"select distinct product, fuel from {source} "  # noqa: S608 (consulta fixa)
        "order by product = 'lpg', product = 'diesel'",
        [str(prices)],
    )
    portugal = _table(
        db,
        f"select {', '.join(PORTUGAL_COLUMNS)} from {source} "  # noqa: S608 (colunas fixas)
        "where country_code = 'PT' order by product, week",
        [str(prices)],
    )
    neighbours = _table(
        db,
        f"select week, product, country_code, price from {source} "  # noqa: S608 (fixa)
        "where country_code in ('ES', 'EU') order by product, country_code, week",
        [str(prices)],
    )
    latest = _table(
        db,
        f"""
        select product, week, {", ".join(COUNTRY_COLUMNS)}
        from {source} as prices
        where week = (select max(week) from {source} where product = prices.product)
            and not is_average
        order by product, price desc
        """,  # noqa: S608 (colunas fixas)
        [str(prices), str(prices)],
    )
    countries = dict(
        db.execute(
            f"select distinct country_code, country from {source}",  # noqa: S608 (fixa)
            [str(prices)],
        ).fetchall()
    )
    downloaded_at = None
    if manifest is not None and manifest.exists():
        downloaded_at = json.loads(manifest.read_text("utf-8")).get("downloaded_at")
    weeks = sorted({row[0] for row in portugal})
    _write_json(
        target / "boletim.json",
        {
            "downloaded_at": downloaded_at,
            "weeks": len(weeks),
            "first_week": weeks[0] if weeks else None,
            "last_week": weeks[-1] if weeks else None,
            "products": [{"product": p, "name": n} for p, n in products],
            "countries": countries,
            "portugal": {"columns": PORTUGAL_COLUMNS, "rows": portugal},
            "neighbours": {
                "columns": ("week", "product", "country_code", "price"),
                "rows": neighbours,
            },
            "latest": {"columns": ("product", "week", *COUNTRY_COLUMNS), "rows": latest},
        },
    )
    rows = _rows(db, f"select * from {source} order by target_week, product", [str(forecast)])  # noqa: S608
    _write_json(target / "previsao.json", {"rows": rows})
    return len(weeks)
