"""Preço de cada posto de abastecimento em Portugal, do portal da DGEG
(https://precoscombustiveis.dgeg.gov.pt).

O portal não tem uma API documentada: usa-se a mesma que a página de pesquisa usa, com todos
os postos de uma vez. A DGEG só mostra o preço em vigor, por isso guarda-se uma fotografia por
dia (ADR 0003). Os termos do portal permitem a reutilização, identificando a DGEG como fonte,
com a data e hora da última atualização dos preços e sem alterar a informação.
"""

from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

API_URL = "https://precoscombustiveis.dgeg.gov.pt/api/PrecoComb"
# Combustíveis rodoviários líquidos e GPL: identificador da DGEG → (código, nome na DGEG).
FUELS = {
    3201: ("gasolina_95", "Gasolina simples 95"),
    3205: ("gasolina_95_especial", "Gasolina especial 95"),
    3400: ("gasolina_98", "Gasolina 98"),
    3405: ("gasolina_98_especial", "Gasolina especial 98"),
    2101: ("gasoleo", "Gasóleo simples"),
    2105: ("gasoleo_especial", "Gasóleo especial"),
    1120: ("gpl", "GPL Auto"),
}
_CODES = {name: code for code, name in FUELS.values()}
# Uma página com todos os postos: hoje são cerca de 3000 por combustível.
_PAGE_SIZE = 100_000
_FIELDS = ("Id", "Nome", "TipoPosto", "Municipio", "Preco", "Marca", "Combustivel")


class DgegFormatError(ValueError):
    """A resposta do portal não tem o formato esperado (a DGEG pode tê-lo mudado)."""


@dataclass(frozen=True, slots=True)
class StationPrice:
    snapshot_date: date  # o dia da fotografia
    station_id: int
    name: str
    brand: str
    station_type: str  # Auto-estrada, Área comercial (Hipermercados) ou Outro
    district: str
    municipality: str
    address: str
    locality: str
    postal_code: str
    latitude: float | None
    longitude: float | None
    fuel: str  # gasolina_95, gasoleo, gpl, …
    price: float  # euros por litro, com impostos
    updated_at: datetime  # quando o posto comunicou este preço


def search_url() -> str:
    """O pedido que traz todos os postos e os preços dos combustíveis de FUELS."""
    query = urllib.parse.urlencode(
        {
            "idsTiposComb": ",".join(str(i) for i in FUELS),
            "qtdPorPagina": _PAGE_SIZE,
            "pagina": 1,
        }
    )
    return f"{API_URL}/PesquisarPostos?{query}"


def read_prices(data: bytes, snapshot_date: date) -> list[StationPrice]:
    """Lê a resposta do PesquisarPostos (JSON)."""
    try:
        body = json.loads(data)
    except ValueError as exc:
        raise DgegFormatError(f"A resposta não é JSON: {exc}") from exc
    if not isinstance(body, dict) or body.get("status") is not True:
        raise DgegFormatError(f"O portal respondeu sem sucesso: {str(body)[:200]}")
    rows = body.get("resultado")
    if not isinstance(rows, list) or not rows:
        raise DgegFormatError("A resposta não tem postos")
    # Cada linha diz quantas há no total: se vierem menos, a página cortou a lista.
    total = rows[0].get("Quantidade")
    if total != len(rows):
        raise DgegFormatError(f"Vieram {len(rows)} preços, mas o portal diz que há {total}")
    return [_station_price(row, snapshot_date) for row in rows]


def _station_price(row: Any, snapshot_date: date) -> StationPrice:
    missing = [f for f in _FIELDS if not isinstance(row, dict) or row.get(f) in (None, "")]
    if missing:
        raise DgegFormatError(f"Faltam os campos {missing} em {str(row)[:200]}")
    fuel = _CODES.get(row["Combustivel"])
    if fuel is None:
        raise DgegFormatError(f"Combustível desconhecido: {row['Combustivel']!r}")
    return StationPrice(
        snapshot_date=snapshot_date,
        station_id=int(row["Id"]),
        name=str(row["Nome"]).strip(),
        brand=str(row["Marca"]).strip(),
        station_type=str(row["TipoPosto"]).strip(),
        district=str(row.get("Distrito") or "").strip(),
        municipality=str(row["Municipio"]).strip(),
        address=str(row.get("Morada") or "").strip(),
        locality=str(row.get("Localidade") or "").strip(),
        postal_code=str(row.get("CodPostal") or "").strip(),
        latitude=_coordinate(row.get("Latitude")),
        longitude=_coordinate(row.get("Longitude")),
        fuel=fuel,
        price=_price(row["Preco"]),
        updated_at=_timestamp(row.get("DataAtualizacao")),
    )


def _price(text: Any) -> float:
    """'1,879 €' → 1.879"""
    cleaned = str(text).replace("€", "").strip().replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError as exc:
        raise DgegFormatError(f"Preço inválido: {text!r}") from exc


def _coordinate(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and value != 0 else None


def _timestamp(text: Any) -> datetime:
    try:
        return datetime.strptime(str(text), "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise DgegFormatError(f"Data de atualização inválida: {text!r}") from exc
