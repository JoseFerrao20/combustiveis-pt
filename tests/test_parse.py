"""Leitura do ficheiro, com uma amostra do real (scripts/make_sample.py)."""

import io
from datetime import date, datetime

import openpyxl
import pytest

from combustiveis.parse import FormatError, Price, read_bulletin


def price(prices: list[Price], **match: object) -> float:
    [found] = [p for p in prices if all(getattr(p, k) == v for k, v in match.items())]
    return found.value


def test_prices_from_the_sample(sample_bytes: bytes) -> None:
    bulletin = read_bulletin(sample_bytes)

    assert bulletin.latest_week == date(2026, 10, 19)
    assert {p.country for p in bulletin.prices} == {"EU", "PT", "ES"}
    assert {p.product for p in bulletin.prices} == {
        "euro95",
        "diesel",
        "heating_oil",
        "fuel_oil_1",
        "fuel_oil_2",
        "lpg",
    }
    week = {"week": date(2026, 10, 19), "country": "PT", "product": "euro95"}
    assert price(bulletin.prices, tax_status="with_tax", **week) == 2099.0
    assert price(bulletin.prices, tax_status="without_tax", **week) == pytest.approx(1121.776, 1e-6)
    # As notas no fim da folha e as linhas de cabeçalho não viram preços.
    assert len({p.week for p in bulletin.prices}) == 5


def test_taxes_from_the_sample(sample_bytes: bytes) -> None:
    taxes = read_bulletin(sample_bytes).taxes

    def tax(kind: str, since: date, product: str = "euro95") -> float:
        [found] = [
            t
            for t in taxes
            if (t.tax, t.country, t.since, t.product) == (kind, "PT", since, product)
        ]
        return found.value

    assert tax("excise", date(2026, 10, 19)) == 425.62  # ISP, € por 1000 L
    assert tax("other", date(2026, 1, 1)) == 159.11
    assert tax("vat", date(2011, 1, 1)) == 23
    # Células vazias são "sem dados", não zero.
    assert all(t.value is not None for t in taxes)
    assert {t.tax for t in taxes} == {"vat", "excise", "other"}


def test_price_is_the_sum_of_its_parts(sample_bytes: bytes) -> None:
    # Em Portugal, o preço com impostos é (produto + ISP + outros impostos) com IVA.
    bulletin = read_bulletin(sample_bytes)
    week = {"week": date(2026, 10, 19), "country": "PT"}
    for product, excise, other in (("euro95", 425.62, 159.11), ("diesel", 259.49, 173.34)):
        net = price(bulletin.prices, tax_status="without_tax", product=product, **week)
        total = price(bulletin.prices, tax_status="with_tax", product=product, **week)
        assert (net + excise + other) * 1.23 == pytest.approx(total, abs=0.01)


def workbook_bytes(sheets: dict[str, list[list[object]]]) -> bytes:
    book = openpyxl.Workbook()
    book.remove(book.active)
    for name, rows in sheets.items():
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def minimal(prices_header: list[object]) -> dict[str, list[list[object]]]:
    rows: list[list[object]] = [
        prices_header,
        [None],
        ["Date"],
        [datetime(2026, 1, 5), None, 1.5],
        ["Notes:", "…"],
    ]
    return {
        "Prices with taxes": rows,
        "Prices wo taxes": rows,
        "VAT": [["PT_", datetime(2011, 1, 1), 23]],
        "Excise duties": [],
        "Other Indirect Taxes": [],
    }


def test_minimal_workbook() -> None:
    bulletin = read_bulletin(workbook_bytes(minimal(["t", "CTR", "PT_price_with_tax_LPG"])))
    assert [(p.country, p.product, p.value) for p in bulletin.prices] == [
        ("PT", "lpg", 1.5),
        ("PT", "lpg", 1.5),
    ]


@pytest.mark.parametrize(
    ("data", "message"),
    ids=["nao-e-excel", "faltam-folhas", "sem-colunas", "sem-precos"],
    argvalues=[
        (b"isto nao e um excel", "Excel válido"),
        (workbook_bytes({"Prices with taxes": [["x"]]}), "Faltam as folhas"),
        (workbook_bytes(minimal(["t", "CTR", "preco"])), "não tem colunas"),
        (
            workbook_bytes(
                minimal(["t", "CTR", "PT_price_with_tax_LPG"])
                | {
                    "Prices with taxes": [["t", "CTR", "PT_price_with_tax_LPG"]],
                    "Prices wo taxes": [["t", "CTR", "PT_price_wo_tax_LPG"]],
                }
            ),
            "nenhum preço",
        ),
    ],
)
def test_format_errors(data: bytes, message: str) -> None:
    with pytest.raises(FormatError, match=message):
        read_bulletin(data)
