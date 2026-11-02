import json
from datetime import date
from pathlib import Path

import duckdb
import pytest

from combustiveis import __main__ as cli
from combustiveis.site import COLUMNS, export_site, forecast_text

STATIONS = """
select * from (values
    (date '2026-11-02', 1, 'Posto A', 'GALP', 'Outro', 'Porto', 'Porto', 'Paranhos', 41.17, -8.60,
     'gasoleo', 'Gasóleo', 1.899, timestamp '2026-11-02 07:30', true, -0.01, date '2026-10-26',
     date '2026-11-02', '02/11: 1,899 · 26/10: 1,909'),
    (date '2026-11-02', 2, 'Posto B', 'BP', 'Auto-estrada', 'Porto', 'Maia', 'Maia', 41.23, -8.62,
     'gasoleo', 'Gasóleo', 1.799, timestamp '2026-11-01 20:00', true, null, null, null, null),
    -- Sem o preço atualizado nos últimos 30 dias: não entra.
    (date '2026-11-02', 3, 'Posto C', 'BP', 'Outro', 'Lisboa', 'Lisboa', 'Lisboa', 38.72, -9.14,
     'gasoleo', 'Gasóleo', 1.500, timestamp '2026-08-01 10:00', false, null, null, null, null),
    -- Sem coordenadas: não entra.
    (date '2026-11-02', 4, 'Posto D', 'BP', 'Outro', 'Lisboa', 'Lisboa', 'Lisboa', null, null,
     'gasoleo', 'Gasóleo', 1.700, timestamp '2026-11-02 09:00', true, null, null, null, null),
    (date '2026-11-02', 1, 'Posto A', 'GALP', 'Outro', 'Porto', 'Porto', 'Paranhos', 41.17, -8.60,
     'gasolina_95', 'Gasolina 95', 1.959, timestamp '2026-11-02 07:30', true, 0.0,
     date '2026-10-26', null, null)
) as t(snapshot_date, station_id, station_name, brand, station_type, district, municipality,
       locality, latitude, longitude, fuel, fuel_name, price, updated_at, is_current,
       change_since_previous, previous_snapshot_date, last_change_date, recent_history)
"""

FORECAST = """
select * from (values
    (date '2026-10-26', 'euro95', 'Gasolina 95', 0.02, null),
    (date '2026-11-02', 'diesel', 'Gasóleo', -0.0642, -0.051),
    (date '2026-11-02', 'euro95', 'Gasolina 95', -0.0137, null)
) as t(target_week, product, product_name, predicted_change, dgeg_change)
"""


def _parquet(tmp_path: Path, name: str, query: str) -> Path:
    path = tmp_path / name
    duckdb.sql(f"copy ({query}) to '{path}' (format parquet)")
    return path


@pytest.fixture
def sources(tmp_path: Path) -> tuple[Path, Path]:
    return _parquet(tmp_path, "postos.parquet", STATIONS), _parquet(
        tmp_path, "previsao.parquet", FORECAST
    )


def test_writes_one_file_per_fuel_with_the_current_stations(
    tmp_path: Path, sources: tuple[Path, Path]
) -> None:
    result = export_site(*sources, tmp_path / "dados")
    assert result.snapshot_date == date(2026, 11, 2)
    # A gasolina 95 vem antes do gasóleo, como no filtro do painel.
    assert result.stations == {"gasolina_95": 1, "gasoleo": 2}

    gasoleo = json.loads((tmp_path / "dados" / "postos-gasoleo.json").read_text("utf-8"))
    assert gasoleo["fuel_name"] == "Gasóleo"
    assert gasoleo["columns"] == list(COLUMNS)
    stations = [dict(zip(gasoleo["columns"], row, strict=True)) for row in gasoleo["stations"]]
    # Do mais barato para o mais caro, sem os desatualizados nem os sem coordenadas.
    assert [s["station_id"] for s in stations] == [2, 1]
    assert stations[1]["updated_at"] == "2026-11-02T07:30:00Z"
    assert stations[1]["previous_snapshot_date"] == "2026-10-26"
    assert stations[1]["recent_history"] == "02/11: 1,899 · 26/10: 1,909"
    assert stations[0]["change_since_previous"] is None


def test_the_summary_has_the_fuels_districts_and_forecast(
    tmp_path: Path, sources: tuple[Path, Path]
) -> None:
    export_site(*sources, tmp_path)
    summary = json.loads((tmp_path / "resumo.json").read_text("utf-8"))
    assert summary["snapshot_date"] == "2026-11-02"
    assert summary["updated_at"] == "2026-11-02T09:00:00Z"
    assert summary["fuels"] == [
        {"fuel": "gasolina_95", "name": "Gasolina 95", "stations": 1},
        {"fuel": "gasoleo", "name": "Gasóleo", "stations": 2},
    ]
    assert summary["districts"] == {"Lisboa": ["Lisboa"], "Porto": ["Maia", "Porto"]}
    assert summary["forecast"].startswith("Previsão para segunda-feira, 02/11: Gasolina 95")


def test_forecast_text() -> None:
    rows = [
        {"target_week": date(2026, 11, 2), "product": "diesel", "product_name": "Gasóleo",
         "predicted_change": -0.0642, "dgeg_change": -0.051},
        {"target_week": date(2026, 11, 2), "product": "euro95", "product_name": "Gasolina 95",
         "predicted_change": 0.0004, "dgeg_change": None},
        {"target_week": date(2026, 10, 26), "product": "euro95", "product_name": "Gasolina 95",
         "predicted_change": 0.02, "dgeg_change": 0.01},
    ]  # fmt: skip
    assert forecast_text(rows) == (
        "Previsão para segunda-feira, 02/11: Gasolina 95 = 0,0 cêntimos,"
        " Gasóleo ▼ \u22126,4 cêntimos por litro (estimativa, sem mudanças do ISP)."
        " Nos postos, a mudança foi de"
        " Gasóleo ▼ \u22125,1 cêntimos."
    )
    rows[1]["predicted_change"] = 0.015
    assert "Gasolina 95 ▲ +1,5 cêntimos" in (forecast_text(rows) or "")
    assert forecast_text([]) is None


def test_command_line(
    tmp_path: Path, sources: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    stations, forecast = sources
    args = ["site", "--postos", str(stations), "--previsao", str(forecast)]
    assert cli.main([*args, "--destino", str(tmp_path / "dados")]) == 0
    assert "Página inicial: postos de 2026-11-02 (gasolina_95: 1, gasoleo: 2)" in (
        capsys.readouterr().out
    )
    assert cli.main(["site", "--postos", str(tmp_path / "nada.parquet")]) == 1
    assert "erro:" in capsys.readouterr().err
