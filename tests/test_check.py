from datetime import date
from pathlib import Path

import pytest

from combustiveis import __main__ as cli
from combustiveis.check import SnapshotError, check_snapshots
from combustiveis.dgeg import read_prices
from combustiveis.landing import write_station_snapshot

SAMPLE = Path(__file__).parent / "fixtures" / "dgeg_sample.json"
TODAY = date(2026, 10, 30)


def snapshot(directory: Path, day: date, stations: int | None = None) -> None:
    prices = read_prices(SAMPLE.read_bytes(), day)
    if stations is not None:
        keep = sorted({p.station_id for p in prices})[:stations]
        prices = [p for p in prices if p.station_id in keep]
    write_station_snapshot(prices, directory)


def test_a_recent_snapshot_passes(tmp_path: Path) -> None:
    snapshot(tmp_path, date(2026, 10, 28))
    snapshot(tmp_path, date(2026, 10, 29))

    result = check_snapshots(tmp_path, max_age_days=2, today=TODAY)

    assert (result.latest, result.stations) == (date(2026, 10, 29), 37)
    assert (result.previous, result.previous_stations) == (date(2026, 10, 28), 37)


def test_the_first_snapshot_has_nothing_to_compare(tmp_path: Path) -> None:
    snapshot(tmp_path, date(2026, 10, 29))
    assert check_snapshots(tmp_path, max_age_days=2, today=TODAY).previous is None


def test_an_old_snapshot_fails(tmp_path: Path) -> None:
    snapshot(tmp_path, date(2026, 10, 27))
    with pytest.raises(SnapshotError, match="há 3 dias"):
        check_snapshots(tmp_path, max_age_days=2, today=TODAY)


def test_no_snapshots_fail(tmp_path: Path) -> None:
    (tmp_path / "notas.parquet").write_bytes(b"")
    with pytest.raises(SnapshotError, match="Não há fotografias"):
        check_snapshots(tmp_path, max_age_days=2, today=TODAY)


def test_a_big_drop_in_stations_fails(tmp_path: Path) -> None:
    snapshot(tmp_path, date(2026, 10, 28))
    snapshot(tmp_path, date(2026, 10, 29), stations=20)
    with pytest.raises(SnapshotError, match="tem 20 postos, e a de 2026-10-28 tinha 37"):
        check_snapshots(tmp_path, max_age_days=2, today=TODAY)


def test_a_small_drop_passes(tmp_path: Path) -> None:
    snapshot(tmp_path, date(2026, 10, 28))
    snapshot(tmp_path, date(2026, 10, 29), stations=32)
    assert check_snapshots(tmp_path, max_age_days=2, today=TODAY).stations == 32


def test_command_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    snapshot(tmp_path, date(2026, 10, 28))
    snapshot(tmp_path, date(2026, 10, 29))
    args = ["verificar-dgeg", "--pasta", str(tmp_path), "--hoje", "2026-10-30"]

    assert cli.main(args) == 0
    assert "Última fotografia da DGEG: 2026-10-29, com 37 postos (37 em 2026-10-28)" in (
        capsys.readouterr().out
    )
    assert cli.main([*args[:-1], "2026-11-05"]) == 1
    assert "erro: A última fotografia da DGEG é de 2026-10-29, há 7 dias" in capsys.readouterr().err
