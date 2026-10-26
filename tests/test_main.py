import json
from pathlib import Path

import duckdb
import pytest
from conftest import SAMPLE

from combustiveis import __main__ as cli
from combustiveis.source import PAGE_URL

HISTORY = "/document/download/1_en?filename=Weekly_Oil_Bulletin_Prices_History.xlsx"


def test_ingest_from_a_local_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["ingest", "--ficheiro", str(SAMPLE), "--destino", str(tmp_path)]) == 0

    assert "160 preços e 198 impostos, até à semana de 2026-10-19" in capsys.readouterr().out
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["latest_week"] == "2026-10-19"
    assert manifest["source_url"].startswith("file://")
    assert len(manifest["sha256"]) == 64
    db = duckdb.connect()
    prices = db.sql(f"SELECT * FROM '{tmp_path / 'prices.parquet'}'")
    assert prices.columns == ["week", "country", "product", "tax_status", "value"]
    assert [str(t) for t in prices.types] == ["DATE", "VARCHAR", "VARCHAR", "VARCHAR", "DOUBLE"]
    assert db.sql(f"SELECT count(*) FROM '{tmp_path / 'taxes.parquet'}'").fetchall() == [(198,)]


def test_ingest_downloads_the_page_then_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    requested = []

    def fake_fetch(url: str) -> bytes:
        requested.append(url)
        if url == PAGE_URL:
            return f'<a href="{HISTORY}">'.encode()
        return SAMPLE.read_bytes()

    monkeypatch.setattr(cli, "fetch", fake_fetch)

    assert cli.main(["ingest", "--destino", str(tmp_path)]) == 0
    assert requested == [PAGE_URL, "https://energy.ec.europa.eu" + HISTORY]
    assert json.loads((tmp_path / "manifest.json").read_text())["source_url"] == requested[1]


def test_errors_exit_with_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "x.xlsx"
    bad.write_bytes(b"nada")
    assert cli.main(["ingest", "--ficheiro", str(bad), "--destino", str(tmp_path)]) == 1
    assert "erro: Não é um ficheiro Excel válido" in capsys.readouterr().err
    assert not (tmp_path / "prices.parquet").exists()
