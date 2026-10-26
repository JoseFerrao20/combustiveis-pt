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


@dataclass(frozen=True, slots=True)
class Manifest:
    source_url: str
    downloaded_at: str  # ISO 8601, em UTC
    sha256: str
    latest_week: str
    prices: int
    taxes: int


def _write_parquet(rows: list[dict[str, object]], schema: dict[str, str], target: Path) -> None:
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
    _write_parquet(
        [asdict(p) for p in bulletin.prices], PRICES_SCHEMA, directory / "prices.parquet"
    )
    _write_parquet([asdict(t) for t in bulletin.taxes], TAXES_SCHEMA, directory / "taxes.parquet")
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
