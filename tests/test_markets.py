from datetime import date
from pathlib import Path

import duckdb
import pytest

from combustiveis import __main__ as cli
from combustiveis.markets import SERIES, MarketFormatError, read_series, series_url

FRED = Path(__file__).parent / "fixtures" / "fred"


def test_reads_a_real_series() -> None:
    values = read_series((FRED / "DGASNYH.csv").read_bytes(), "DGASNYH")

    assert values[0].day == date(2026, 8, 17)
    assert values[-1].day == date(2026, 10, 27)
    assert all(v.series == "DGASNYH" and 0.5 < v.value < 10 for v in values)


def test_days_without_a_quote_are_left_out() -> None:
    data = (
        b"observation_date,DEXUSEU\n2026-10-22,1.12\n2026-10-23,.\n2026-10-26,\n2026-10-27,1.13\n"
    )
    values = read_series(data, "DEXUSEU")
    assert [(v.day, v.value) for v in values] == [
        (date(2026, 10, 22), 1.12),
        (date(2026, 10, 27), 1.13),
    ]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"DATE,DEXUSEU\n2026-10-22,1.12\n", "cabeçalho inesperado"),
        (b"observation_date,DGASNYH\n2026-10-22,1.12\n", "cabeçalho inesperado"),
        (b"", "cabeçalho inesperado"),
        (b"observation_date,DEXUSEU\n22/10/2026,1.12\n", "data inválida"),
        (b"observation_date,DEXUSEU\n2026-10-23,1.1\n2026-10-22,1.2\n", "fora de ordem"),
        (b"observation_date,DEXUSEU\n2026-10-22,1,12\n", "esperava 2 colunas"),
        (b"observation_date,DEXUSEU\n2026-10-22,abc\n", "valor inválido"),
        (b"observation_date,DEXUSEU\n2026-10-22,-1\n", "não positivo"),
        (b"observation_date,DEXUSEU\n2026-10-22,.\n", "sem valores"),
    ],
)
def test_rejects_unexpected_files(data: bytes, message: str) -> None:
    with pytest.raises(MarketFormatError, match=message):
        read_series(data, "DEXUSEU")


def test_series_url() -> None:
    assert series_url("DEXUSEU") == "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSEU"
    with pytest.raises(ValueError, match="desconhecida"):
        series_url("XPTO")


def test_command_line_from_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "mercados.parquet"
    assert cli.main(["mercados", "--ficheiros", str(FRED), "--destino", str(target)]) == 0

    assert "DGASNYH até 2026-10-27" in capsys.readouterr().out
    rows = duckdb.connect().sql(f"SELECT DISTINCT series FROM '{target}' ORDER BY 1").fetchall()
    assert [r[0] for r in rows] == sorted(SERIES)


def test_command_line_downloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    requested = []

    def fake_fetch(url: str) -> bytes:
        requested.append(url)
        return (FRED / f"{url.rsplit('=', 1)[1]}.csv").read_bytes()

    monkeypatch.setattr(cli, "fetch", fake_fetch)
    assert cli.main(["mercados", "--destino", str(tmp_path / "m.parquet")]) == 0
    assert requested == [series_url(s) for s in SERIES]


def test_a_bad_file_exits_with_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for series in SERIES:
        (tmp_path / f"{series}.csv").write_text("x,y\n")
    assert (
        cli.main(["mercados", "--ficheiros", str(tmp_path), "--destino", str(tmp_path / "m")]) == 1
    )
    assert "cabeçalho inesperado" in capsys.readouterr().err
