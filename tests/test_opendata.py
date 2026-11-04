import csv
import gzip
from datetime import date
from pathlib import Path

import duckdb
import pytest

from combustiveis import __main__ as cli
from combustiveis.opendata import export_open_data

SNAPSHOT = date(2026, 11, 2)


@pytest.fixture
def warehouse(tmp_path: Path) -> Path:
    path = tmp_path / "warehouse.duckdb"
    db = duckdb.connect(str(path))
    db.execute("""
        create table fct_station_prices as select * from (values
            (date '2026-10-26', 1, 'POSTO A', 'GALP', 'Outro', 'Porto', 'Porto', 'Paranhos',
             'Rua A', '4200-001', 41.17, -8.60, 'gasoleo', 1.909,
             timestamp '2026-10-26 07:30', true),
            (date '2026-11-02', 1, 'POSTO A', 'GALP', 'Outro', 'Porto', 'Porto', 'Paranhos',
             'Rua A', '4200-001', 41.17, -8.60, 'gasoleo', 1.899,
             timestamp '2026-11-02 07:30', true),
            (date '2026-11-02', 2, 'POSTO B', 'BP', 'Outro', 'Porto', 'Maia', 'Maia',
             'Rua B', '4470-001', 41.23, -8.62, 'gasoleo', 1.799,
             timestamp '2026-11-01 20:00', true)
        ) as t(snapshot_date, station_id, station_name, brand, station_type, district,
               municipality, locality, address, postal_code, latitude, longitude, fuel, price,
               updated_at, is_current)
    """)
    db.execute("create table dgeg_fuels as select 'gasoleo' as fuel, 'Gasóleo' as name")
    db.execute("""
        create table fct_fuel_prices as select * from (values
            (date '2005-01-03', 'PT', 'euro95', 1000.123456, 500.0, 300.0, 200.0, 21.0, 500.0, 0.5),
            (date '2026-10-19', 'PT', 'euro95', 2099.0, 1122.0, 585.0, 392.0, 23.0, 977.0, 0.465)
        ) as t(week, country_code, product, price_with_tax, price_without_tax,
               excise_and_other_taxes, vat_amount, vat_rate, taxes_total, tax_share)
    """)
    db.execute(
        "create table countries as select 'PT' as country_code, 'Portugal' as name, "
        "date '2002-01-01' as euro_since"
    )
    db.execute(
        "create table products as select 'euro95' as product, 'Gasolina 95' as name, "
        "'1000 L' as unit"
    )
    db.close()
    return path


def test_writes_the_files_and_the_page(tmp_path: Path, warehouse: Path) -> None:
    files = export_open_data(warehouse, tmp_path / "site", SNAPSHOT)
    assert {f.name: f.rows for f in files} == {
        "postos-historico.csv.gz": 3,
        "postos-ultima-fotografia.csv": 2,
        "boletim-europeu.csv.gz": 2,
    }
    folder = tmp_path / "site" / "dados-abertos"
    with gzip.open(folder / "postos-historico.csv.gz", "rt", encoding="utf-8") as f:
        history = list(csv.DictReader(f))
    assert [row["snapshot_date"] for row in history] == ["2026-10-26", "2026-11-02", "2026-11-02"]
    assert history[0]["fuel_name"] == "Gasóleo"
    assert history[0]["price"] == "1.909"
    latest = list(csv.DictReader((folder / "postos-ultima-fotografia.csv").open(encoding="utf-8")))
    assert {row["station_id"] for row in latest} == {"1", "2"}
    with gzip.open(folder / "boletim-europeu.csv.gz", "rt", encoding="utf-8") as f:
        bulletin = list(csv.DictReader(f))
    # Os valores arredondados, com o país e o produto por extenso.
    assert bulletin[0]["price_with_tax"] == "1000.12"
    assert bulletin[0]["country"] == "Portugal"
    assert bulletin[0]["product_name"] == "Gasolina 95"
    page = (folder / "index.html").read_text("utf-8")
    assert "<h1>Dados abertos</h1>" in page
    assert '<a href="postos-historico.csv.gz" download>' in page
    assert "03/01/2005 a 19/10/2026" in page


def test_command_line_with_and_without_the_warehouse(
    tmp_path: Path, warehouse: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stations = tmp_path / "postos.parquet"
    forecast = tmp_path / "previsao.parquet"
    from test_site import FORECAST, STATIONS

    duckdb.sql(f"copy ({STATIONS}) to '{stations}' (format parquet)")
    duckdb.sql(f"copy ({FORECAST}) to '{forecast}' (format parquet)")
    args = ["site", "--postos", str(stations), "--previsao", str(forecast)]
    args += ["--destino", str(tmp_path / "dados"), "--paginas", str(tmp_path / "site")]
    assert cli.main([*args, "--armazem", str(warehouse)]) == 0
    assert "Dados abertos em" in capsys.readouterr().out
    assert (tmp_path / "site" / "dados-abertos" / "index.html").exists()
    # Sem a base de dados do dbt, não há dados abertos (e não é um erro).
    assert cli.main([*args, "--armazem", str(tmp_path / "nada.duckdb")]) == 0
    assert "Dados abertos" not in capsys.readouterr().out


def test_includes_the_islands_when_the_warehouse_has_them(tmp_path: Path, warehouse: Path) -> None:
    db = duckdb.connect(str(warehouse))
    db.execute("""
        create table stg_ilhas__max_prices as select * from (values
            ('madeira', 'gasoleo', date '2026-11-02', 2.125, 'Despacho Conjunto n.º 99/2026',
             date '2026-10-30', 'https://joram.madeira.gov.pt/x.pdf')
        ) as t(region, fuel, valid_from, price, act, published, source_url)
    """)
    db.close()
    files = export_open_data(warehouse, tmp_path / "site", SNAPSHOT)
    assert {f.name: f.rows for f in files}["ilhas-precos-maximos.csv"] == 1
    page = (tmp_path / "site" / "dados-abertos" / "index.html").read_text("utf-8")
    assert 'href="ilhas-precos-maximos.csv"' in page
    assert "Açores e Madeira (preços máximos)" in page
    text = (tmp_path / "site" / "dados-abertos" / "ilhas-precos-maximos.csv").read_text("utf-8")
    assert text.splitlines()[0] == "region,fuel,valid_from,price,act,published,source_url"
