"""Escrita da camada "landing": os dados do boletim em Parquet, tal como vieram, e um
manifesto com a origem (endereço, data da descarga e impressão digital do ficheiro)."""

from __future__ import annotations

import csv
import hashlib
import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from .dgeg import StationPrice
from .markets import MarketValue
from .parse import Bulletin

PRICES_SCHEMA = {
    "week": "DATE",
    "country": "VARCHAR",
    "product": "VARCHAR",
    "tax_status": "VARCHAR",
    "value": "DOUBLE",
}
TAXES_SCHEMA = {
    "tax": "VARCHAR",
    "country": "VARCHAR",
    "since": "DATE",
    "product": "VARCHAR",
    "value": "DOUBLE",
}

STATIONS_SCHEMA = {
    "snapshot_date": "DATE",
    "station_id": "BIGINT",
    "name": "VARCHAR",
    "brand": "VARCHAR",
    "station_type": "VARCHAR",
    "district": "VARCHAR",
    "municipality": "VARCHAR",
    "address": "VARCHAR",
    "locality": "VARCHAR",
    "postal_code": "VARCHAR",
    "latitude": "DOUBLE",
    "longitude": "DOUBLE",
    "fuel": "VARCHAR",
    "price": "DOUBLE",
    "updated_at": "TIMESTAMP",
}

MARKETS_SCHEMA = {"series": "VARCHAR", "day": "DATE", "value": "DOUBLE"}


@dataclass(frozen=True, slots=True)
class Manifest:
    source_url: str
    downloaded_at: str  # ISO 8601, em UTC
    sha256: str
    latest_week: str
    prices: int
    taxes: int


def write_parquet(rows: list[dict[str, object]], schema: dict[str, str], target: Path) -> None:
    # CSV temporário e COPY do DuckDB: tipos explícitos e Parquet sem precisar do pyarrow.
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "rows.csv"
        with staging.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(schema))
            writer.writeheader()
            writer.writerows(rows)
        columns = ", ".join(f"'{name}': '{kind}'" for name, kind in schema.items())
        duckdb.sql(
            f"COPY (SELECT * FROM read_csv('{staging}', header = true, columns = {{{columns}}}))"  # noqa: S608 (nomes das colunas fixos, do código)
            f" TO '{target}' (FORMAT parquet, COMPRESSION zstd)"
        )


def write_landing(bulletin: Bulletin, data: bytes, source_url: str, directory: Path) -> Manifest:
    """Escreve prices.parquet, taxes.parquet e manifest.json em ``directory``."""
    directory.mkdir(parents=True, exist_ok=True)
    write_parquet([asdict(p) for p in bulletin.prices], PRICES_SCHEMA, directory / "prices.parquet")
    write_parquet([asdict(t) for t in bulletin.taxes], TAXES_SCHEMA, directory / "taxes.parquet")
    manifest = Manifest(
        source_url=source_url,
        downloaded_at=datetime.now(UTC).isoformat(timespec="seconds"),
        sha256=hashlib.sha256(data).hexdigest(),
        latest_week=bulletin.latest_week.isoformat(),
        prices=len(bulletin.prices),
        taxes=len(bulletin.taxes),
    )
    (directory / "manifest.json").write_text(
        json.dumps(asdict(manifest), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def write_station_snapshot(prices: list[StationPrice], directory: Path) -> Path:
    """Escreve a fotografia de um dia dos preços da DGEG em ``directory/AAAA-MM-DD.parquet``."""
    days = {p.snapshot_date for p in prices}
    if len(days) != 1:
        raise ValueError(f"Uma fotografia é de um só dia, e esta tem {sorted(days)}")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{days.pop().isoformat()}.parquet"
    write_parquet([asdict(p) for p in prices], STATIONS_SCHEMA, target)
    return target


def write_markets(values: list[MarketValue], target: Path) -> Path:
    """Escreve as séries dos mercados (formato longo: série, dia, valor) num Parquet."""
    target.parent.mkdir(parents=True, exist_ok=True)
    write_parquet([asdict(v) for v in values], MARKETS_SCHEMA, target)
    return target
