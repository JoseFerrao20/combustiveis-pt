"""Preços diários dos mercados internacionais, do FRED (Federal Reserve Bank of St. Louis), para
a previsão do preço de segunda-feira em Portugal: a gasolina e o gasóleo do porto de Nova Iorque,
o Brent (só para comparar) e o câmbio do euro.

O FRED dá cada série num CSV com duas colunas (``observation_date`` e o código da série) e um
valor vazio ou ``.`` nos dias sem cotação. A leitura valida o formato e lança
``MarketFormatError`` em vez de devolver dados errados, como a do boletim.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date

#: Código no FRED → o que é e em que unidade.
SERIES = {
    "DGASNYH": "Gasolina convencional, porto de Nova Iorque (dólares por galão)",
    "DDFUELNYH": "Gasóleo de muito baixo enxofre, porto de Nova Iorque (dólares por galão)",
    "DCOILBRENTEU": "Brent, Europa (dólares por barril)",
    "DEXUSEU": "Câmbio: dólares por euro",
}
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"


class MarketFormatError(ValueError):
    """O CSV do FRED não tem o formato esperado."""


@dataclass(frozen=True, slots=True)
class MarketValue:
    series: str
    day: date
    value: float


def series_url(series: str) -> str:
    if series not in SERIES:
        raise ValueError(f"Série desconhecida: {series}")
    return FRED_URL.format(series=series)


def read_series(data: bytes, series: str) -> list[MarketValue]:
    """Os valores de uma série do FRED, sem os dias sem cotação."""
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    if not rows or [cell.strip() for cell in rows[0]] != ["observation_date", series]:
        header = rows[0] if rows else []
        raise MarketFormatError(f"{series}: cabeçalho inesperado {header}")
    values: list[MarketValue] = []
    previous: date | None = None
    for number, row in enumerate(rows[1:], start=2):
        if len(row) != 2:
            raise MarketFormatError(f"{series}, linha {number}: esperava 2 colunas, tem {len(row)}")
        try:
            day = date.fromisoformat(row[0])
        except ValueError as exc:
            raise MarketFormatError(f"{series}, linha {number}: data inválida {row[0]!r}") from exc
        if previous is not None and day <= previous:
            raise MarketFormatError(f"{series}, linha {number}: datas fora de ordem ({day})")
        previous = day
        text = row[1].strip()
        if text in ("", "."):
            continue
        try:
            value = float(text)
        except ValueError as exc:
            raise MarketFormatError(f"{series}, linha {number}: valor inválido {text!r}") from exc
        if value <= 0:
            raise MarketFormatError(f"{series}, linha {number}: valor não positivo {value}")
        values.append(MarketValue(series, day, value))
    if not values:
        raise MarketFormatError(f"{series}: sem valores")
    return values
