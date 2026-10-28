import json
from datetime import date, datetime
from pathlib import Path

import duckdb
import pytest

from combustiveis import __main__ as cli
from combustiveis.dgeg import FUELS, DgegFormatError, read_prices, search_url
from combustiveis.landing import write_station_snapshot

SAMPLE = Path(__file__).parent / "fixtures" / "dgeg_sample.json"
DAY = date(2026, 10, 28)


def body(rows: list[dict[str, object]]) -> bytes:
    for row in rows:
        row["Quantidade"] = len(rows)
    return json.dumps({"status": True, "mensagem": "sucesso", "resultado": rows}).encode()


def row(**changes: object) -> dict[str, object]:
    base: dict[str, object] = {
        "Id": 1,
        "Nome": "Posto da Ponte ",
        "TipoPosto": "Outro",
        "Municipio": "Ílhavo",
        "Preco": "1,894 €",
        "Marca": "DPP",
        "Combustivel": "Gasolina simples 95",
        "DataAtualizacao": "2026-10-26 16:30",
        "Distrito": "Aveiro",
        "Morada": "Rua de Ílhavo",
        "Localidade": "Gafanha",
        "CodPostal": "3830-488",
        "Latitude": 40.613533,
        "Longitude": -8.726525,
        "Quantidade": 1,
    }
    return {**base, **changes}


def test_reads_the_sample_of_the_real_response() -> None:
    prices = read_prices(SAMPLE.read_bytes(), DAY)

    assert len(prices) == 156
    assert len({p.station_id for p in prices}) == 37
    assert {p.fuel for p in prices} >= {"gasolina_95", "gasoleo"}
    assert {p.snapshot_date for p in prices} == {DAY}
    assert all(0.5 < p.price < 4 for p in prices)


def test_reads_one_price() -> None:
    [price] = read_prices(body([row()]), DAY)

    assert price.name == "Posto da Ponte"
    assert price.brand == "DPP"
    assert price.fuel == "gasolina_95"
    assert price.price == 1.894
    assert price.updated_at == datetime(2026, 10, 26, 16, 30)
    assert (price.latitude, price.longitude) == (40.613533, -8.726525)


def test_missing_coordinates_are_none() -> None:
    [price] = read_prices(body([row(Latitude=None, Longitude=0)]), DAY)
    assert price.latitude is None
    assert price.longitude is None


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"<html>manutencao</html>", "não é JSON"),
        (b'{"status": false, "mensagem": "erro"}', "sem sucesso"),
        (b'{"status": true, "resultado": []}', "não tem postos"),
        (body([row(Preco="")]), "Faltam os campos"),
        (body([row(Combustivel="Hidrogénio")]), "Combustível desconhecido"),
        (body([row(Preco="barato")]), "Preço inválido"),
        (body([row(DataAtualizacao="ontem")]), "Data de atualização inválida"),
    ],
    ids=["html", "status", "empty", "missing", "fuel", "price", "date"],
)
def test_unexpected_responses_fail(data: bytes, message: str) -> None:
    with pytest.raises(DgegFormatError, match=message):
        read_prices(data, DAY)


def test_a_truncated_list_fails() -> None:
    rows = [row(Id=1), row(Id=2)]
    data = json.loads(body(rows))
    data["resultado"] = data["resultado"][:1]
    with pytest.raises(DgegFormatError, match="Vieram 1 preços, mas o portal diz que há 2"):
        read_prices(json.dumps(data).encode(), DAY)


def test_the_request_asks_for_every_fuel_on_one_page() -> None:
    url = search_url()
    assert url.startswith("https://precoscombustiveis.dgeg.gov.pt/api/PrecoComb/PesquisarPostos?")
    assert ",".join(str(i) for i in FUELS) in url.replace("%2C", ",")
    assert "qtdPorPagina=100000" in url


def test_snapshot_is_one_parquet_per_day(tmp_path: Path) -> None:
    prices = read_prices(SAMPLE.read_bytes(), DAY)
    target = write_station_snapshot(prices, tmp_path)

    assert target == tmp_path / "2026-10-28.parquet"
    db = duckdb.connect()
    rows = db.sql(f"SELECT count(*), min(snapshot_date), max(price) FROM '{target}'").fetchall()
    assert rows[0][0] == 156
    assert rows[0][1] == DAY
    columns = {
        name: kind for name, kind, *_ in db.sql(f"DESCRIBE SELECT * FROM '{target}'").fetchall()
    }
    assert columns["price"] == "DOUBLE"
    assert columns["updated_at"] == "TIMESTAMP"
    assert columns["station_id"] == "BIGINT"


def test_a_snapshot_has_one_day(tmp_path: Path) -> None:
    prices = read_prices(SAMPLE.read_bytes(), DAY) + read_prices(body([row()]), date(2026, 10, 29))
    with pytest.raises(ValueError, match="um só dia"):
        write_station_snapshot(prices, tmp_path)


def test_command_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = ["dgeg", "--ficheiro", str(SAMPLE), "--destino", str(tmp_path), "--data", "2026-10-28"]
    assert cli.main(args) == 0
    assert "156 preços de 37 postos, do dia 2026-10-28" in capsys.readouterr().out
    assert (tmp_path / "2026-10-28.parquet").exists()


def test_command_line_downloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    requested = []

    def fake_fetch(url: str) -> bytes:
        requested.append(url)
        return SAMPLE.read_bytes()

    monkeypatch.setattr(cli, "fetch", fake_fetch)
    assert cli.main(["dgeg", "--destino", str(tmp_path)]) == 0
    assert requested == [search_url()]


def test_command_line_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "x.json"
    bad.write_text("{}")
    assert cli.main(["dgeg", "--ficheiro", str(bad), "--destino", str(tmp_path)]) == 1
    assert "erro: O portal respondeu sem sucesso" in capsys.readouterr().err
