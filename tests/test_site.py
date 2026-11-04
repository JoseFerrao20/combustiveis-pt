import json
from datetime import date
from pathlib import Path

import duckdb
import pytest

from combustiveis import __main__ as cli
from combustiveis.site import (
    COLUMNS,
    export_analyses,
    export_history,
    export_islands,
    export_site,
    export_tracked,
    forecast_summary,
    forecast_text,
)

STATIONS = """
select *, 'Petrolíferas' as brand_segment, 2 as competitors_5km from (values
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
    assert summary["stations_total"] == 4
    assert summary["forecast"].startswith("Previsão para segunda-feira, 02/11: Gasolina 95")
    assert summary["forecast_summary"] == {
        "week": "2026-11-02",
        "items": [
            {"name": "Gasolina 95", "predicted": -1.4, "observed": None},
            {"name": "Gasóleo", "predicted": -6.4, "observed": -5.1},
        ],
    }


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
    assert forecast_summary([]) is None


def test_command_line(
    tmp_path: Path, sources: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    stations, forecast = sources
    args = ["site", "--postos", str(stations), "--previsao", str(forecast)]
    # Sem os ficheiros do resumo e dos postos acompanhados, escreve só a página inicial.
    missing = str(tmp_path / "nada.parquet")
    extras = ["--evolucao", missing, "--acompanhados", missing, "--concorrentes", missing]
    assert cli.main([*args, *extras, "--destino", str(tmp_path / "dados")]) == 0
    out = capsys.readouterr().out
    assert "Página inicial: postos de 2026-11-02 (gasolina_95: 1, gasoleo: 2)" in out
    assert "Evolução" not in out
    assert not (tmp_path / "dados" / "acompanhados.json").exists()
    assert cli.main(["site", "--postos", str(tmp_path / "nada.parquet")]) == 1
    assert "erro:" in capsys.readouterr().err


def test_history_has_portugal_first_and_the_brand_groups(tmp_path: Path) -> None:
    daily = _parquet(
        tmp_path,
        "diario.parquet",
        """
        select * from (values
            (date '2026-11-02', 'gasoleo', 'Grupo de marcas', 'Petrolíferas', 1.81234, 10),
            (date '2026-11-02', 'gasoleo', 'Portugal', 'Portugal', 1.79, 30),
            (date '2026-10-26', 'gasoleo', 'Portugal', 'Portugal', 1.80, 29),
            (date '2026-11-02', 'gasoleo', 'Distrito', 'Porto', 1.78, 5)
        ) as t(snapshot_date, fuel, dimension, label, avg_price, stations)
        """,
    )
    assert export_history(daily, tmp_path) == 3
    rows = json.loads((tmp_path / "evolucao.json").read_text("utf-8"))["rows"]
    assert [(r["snapshot_date"], r["label"]) for r in rows] == [
        ("2026-10-26", "Portugal"),
        ("2026-11-02", "Portugal"),
        ("2026-11-02", "Petrolíferas"),
    ]
    assert rows[2]["avg_price"] == 1.8123


def test_tracked_has_the_history_and_the_current_competitors(tmp_path: Path) -> None:
    tracked = _parquet(
        tmp_path,
        "acompanhados.parquet",
        """
        select * from (values
            (date '2026-11-02', 1, 'Posto A (Rua)', 'Rua', 'Posto A', 'GALP', 'Porto', 41.1, -8.6,
             'gasoleo', 'Gasóleo', 1.899, timestamp '2026-11-02 07:30', 4, 1.91, 1.85, 2, 1.92),
            (date '2026-10-26', 1, 'Posto A (Rua)', 'Rua', 'Posto A', 'GALP', 'Porto', 41.1, -8.6,
             'gasoleo', 'Gasóleo', 1.909, timestamp '2026-10-26 07:30', 4, 1.92, 1.86, 3, 1.93),
            -- Sem preço deste combustível: não entra.
            (date '2026-11-02', 1, 'Posto A (Rua)', 'Rua', 'Posto A', 'GALP', 'Porto', 41.1, -8.6,
             'gpl', 'GPL Auto', null, null, 0, null, null, null, null)
        ) as t(snapshot_date, station_id, label, location, station_name, brand, municipality,
               latitude, longitude, fuel, fuel_name, price, updated_at, competitors,
               competitors_avg_price, competitors_min_price, rank_5km, municipality_avg_price)
        """,
    )
    competitors = _parquet(
        tmp_path,
        "concorrentes.parquet",
        """
        select * from (values
            (date '2026-11-02', 1, 7, 'Posto X', 'BP', 41.11, -8.61, 1.234, 'gasoleo', 1.85,
             timestamp '2026-11-02 08:00', true),
            -- Desatualizado ou de uma fotografia antiga: não entram.
            (date '2026-11-02', 1, 8, 'Posto Y', 'BP', 41.12, -8.62, 2.5, 'gasoleo', 1.70,
             timestamp '2026-08-01 08:00', false),
            (date '2026-10-26', 1, 7, 'Posto X', 'BP', 41.11, -8.61, 1.234, 'gasoleo', 1.86,
             timestamp '2026-10-26 08:00', true)
        ) as t(snapshot_date, station_id, competitor_id, station_name, brand, latitude,
               longitude, distance_km, fuel, price, updated_at, is_current)
        """,
    )
    assert export_tracked(tracked, competitors, tmp_path) == 2
    data = json.loads((tmp_path / "acompanhados.json").read_text("utf-8"))
    assert [r["snapshot_date"] for r in data["history"]] == ["2026-10-26", "2026-11-02"]
    assert data["history"][1]["rank_5km"] == 2
    assert [(r["competitor_id"], r["price"], r["distance_km"]) for r in data["competitors"]] == [
        (7, 1.85, 1.23)
    ]


def test_analyses_have_portugal_neighbours_and_the_latest_week(tmp_path: Path) -> None:
    prices = _parquet(
        tmp_path,
        "boletim.parquet",
        """
        select * from (values
            (date '2026-10-12', 'PT', 'Portugal', false, 'euro95', 'Gasolina 95', 2.05, 1.10,
             0.57, 0.38, 0.95, 0.23, 0.4634),
            (date '2026-10-19', 'PT', 'Portugal', false, 'euro95', 'Gasolina 95', 2.099, 1.122,
             0.585, 0.392, 0.977, 0.23, 0.4655),
            (date '2026-10-19', 'ES', 'Espanha', false, 'euro95', 'Gasolina 95', 1.781, 1.199,
             0.273, 0.309, 0.582, 0.21, 0.3268),
            (date '2026-10-19', 'EU', 'União Europeia (média)', true, 'euro95', 'Gasolina 95',
             1.95, 1.1, 0.5, 0.35, 0.85, 0.2, 0.43),
            (date '2026-10-19', 'DK', 'Dinamarca', false, 'euro95', 'Gasolina 95', 2.605, 1.366,
             0.718, 0.521, 1.239, 0.25, 0.4756),
            (date '2026-10-19', 'PT', 'Portugal', false, 'diesel', 'Gasóleo', 2.20, 1.30,
             0.49, 0.41, 0.90, 0.23, 0.409)
        ) as t(week, country_code, country, is_average, product, fuel, price, price_without_tax,
               excise_and_other_taxes, vat_amount, taxes_total, vat_rate, tax_share)
        """,
    )
    forecast = _parquet(tmp_path, "previsao.parquet", FORECAST)
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"downloaded_at": "2026-10-28T17:13:16+00:00"}', "utf-8")

    assert export_analyses(prices, forecast, manifest, tmp_path) == 2
    bulletin = json.loads((tmp_path / "boletim.json").read_text("utf-8"))
    assert bulletin["downloaded_at"] == "2026-10-28T17:13:16+00:00"
    assert (bulletin["first_week"], bulletin["last_week"]) == ("2026-10-12", "2026-10-19")
    # A gasolina antes do gasóleo, como nos filtros.
    assert [p["product"] for p in bulletin["products"]] == ["euro95", "diesel"]
    portugal = [dict(zip(bulletin["portugal"]["columns"], r, strict=True))
                for r in bulletin["portugal"]["rows"]]  # fmt: skip
    assert portugal[-1]["tax_share"] == 0.4655
    assert {r[2] for r in bulletin["neighbours"]["rows"]} == {"ES", "EU"}
    # A última semana: só países (sem as médias), do mais caro para o mais barato.
    latest = [r for r in bulletin["latest"]["rows"] if r[0] == "euro95"]
    assert [r[2] for r in latest] == ["DK", "PT", "ES"]
    forecast_rows = json.loads((tmp_path / "previsao.json").read_text("utf-8"))["rows"]
    assert forecast_rows[0]["target_week"] == "2026-10-26"
    # Sem o manifesto, sem a data da descarga.
    export_analyses(prices, forecast, tmp_path / "nada.json", tmp_path)
    assert json.loads((tmp_path / "boletim.json").read_text("utf-8"))["downloaded_at"] is None


def test_islands_skip_the_empty_row_of_the_dbt_export(tmp_path: Path) -> None:
    islands = _parquet(
        tmp_path,
        "ilhas.parquet",
        """
        select * from (values
            ('madeira', 'Madeira', 'gasoleo', 'Gasóleo', date '2026-11-02', null::date, 2.125,
             'Despacho Conjunto n.º 99/2026', date '2026-10-30', 'https://joram/x.pdf',
             date '2026-11-02', 2.26834, 2915),
            -- Sem preços, o dbt exporta uma linha só com nulos: não entra.
            (null, null, null, null, null, null, null, null, null, null, null, null, null)
        ) as t(region, region_name, fuel, fuel_name, valid_from, valid_to, price, act,
               published, source_url, continent_snapshot, continent_avg_price,
               continent_stations)
        """,
    )
    assert export_islands(islands, tmp_path) == 1
    rows = json.loads((tmp_path / "ilhas.json").read_text("utf-8"))["rows"]
    assert rows[0]["valid_from"] == "2026-11-02"
    assert rows[0]["valid_to"] is None
    assert rows[0]["continent_avg_price"] == 2.2683
