from datetime import date
from pathlib import Path

import duckdb
import pytest
from test_site import FORECAST, STATIONS

from combustiveis import __main__ as cli
from combustiveis.pages import slug, tidy, write_pages

SNAPSHOT = date(2026, 11, 2)


def _parquet(tmp_path: Path, query: str) -> Path:
    path = tmp_path / "postos.parquet"
    duckdb.sql(f"copy ({query}) to '{path}' (format parquet)")
    return path


def test_slug_and_tidy() -> None:
    assert slug("Vila Nova de Gaia") == "vila-nova-de-gaia"
    assert slug("Ílhavo") == "ilhavo"
    assert tidy("INTERMARCHE GAFANHA DA NAZARE") == "Intermarche Gafanha da Nazare"
    assert tidy("AUCHAN Gondomar II") == "Auchan Gondomar II"
    assert tidy("POSTO DPP GAFANHA") == "Posto DPP Gafanha"
    assert tidy("Galp Areeiro") == "Galp Areeiro"
    assert tidy("") == ""


def test_one_page_per_municipality(tmp_path: Path) -> None:
    assert write_pages(_parquet(tmp_path, STATIONS), tmp_path / "site", SNAPSHOT) == 3
    porto = (tmp_path / "site" / "concelho" / "porto" / "index.html").read_text("utf-8")
    assert "<title>Combustível mais barato em Porto</title>" in porto
    assert (
        '<link rel="canonical" href="https://joseferrao20.github.io/combustiveis-pt/concelho/porto/">'
        in porto
    )
    # O preço, a data e a hora da atualização, e o link para o posto no mapa.
    assert "1,899 €" in porto
    assert "02/11/2026 07:30" in porto
    assert "?posto=1&amp;combustivel=gasoleo" in porto
    assert 'href="../../?concelho=Porto"' in porto
    # Os outros concelhos do distrito.
    assert '<a href="../../concelho/maia/">Maia</a>' in porto
    # Em Lisboa, o posto com o preço antigo fica de fora (o sem coordenadas entra).
    lisboa = (tmp_path / "site" / "concelho" / "lisboa" / "index.html").read_text("utf-8")
    assert "Posto D" in lisboa
    assert "Posto C" not in lisboa


def test_old_pages_are_removed(tmp_path: Path) -> None:
    old = tmp_path / "concelho" / "de-outro-ano"
    old.mkdir(parents=True)
    (old / "index.html").write_text("velha")
    write_pages(_parquet(tmp_path, STATIONS), tmp_path, SNAPSHOT)
    assert not old.exists()


def test_index_and_sitemap(tmp_path: Path) -> None:
    write_pages(_parquet(tmp_path, STATIONS), tmp_path, SNAPSHOT)
    index = (tmp_path / "concelho" / "index.html").read_text("utf-8")
    assert "<h2>Porto</h2>" in index
    assert '<a href="maia/">Maia</a>' in index
    sitemap = (tmp_path / "sitemap.xml").read_text("utf-8")
    assert "<loc>https://joseferrao20.github.io/combustiveis-pt/</loc>" in sitemap
    assert "<loc>https://joseferrao20.github.io/combustiveis-pt/resumo/</loc>" in sitemap
    assert "<loc>https://joseferrao20.github.io/combustiveis-pt/concelho/porto/</loc>" in sitemap
    assert "<lastmod>2026-11-02</lastmod>" in sitemap


def test_same_name_in_two_districts(tmp_path: Path) -> None:
    two = STATIONS.replace(
        "'Lisboa', 'Lisboa', 'Lisboa', null", "'Lisboa', 'Porto', 'Lisboa', null"
    )
    # Porto (Porto), Maia e Porto (Lisboa): Lisboa fica sem postos atualizados.
    assert write_pages(_parquet(tmp_path, two), tmp_path, SNAPSHOT) == 3
    assert (tmp_path / "concelho" / "porto-porto" / "index.html").exists()
    assert (tmp_path / "concelho" / "porto-lisboa" / "index.html").exists()


def test_command_line_writes_the_pages(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    stations = _parquet(tmp_path, STATIONS)
    forecast = tmp_path / "previsao.parquet"
    duckdb.sql(f"copy ({FORECAST}) to '{forecast}' (format parquet)")
    args = ["site", "--postos", str(stations), "--previsao", str(forecast)]
    args += ["--destino", str(tmp_path / "dados"), "--paginas", str(tmp_path)]
    assert cli.main(args) == 0
    assert "Páginas por concelho: 3" in capsys.readouterr().out
    assert (tmp_path / "concelho" / "maia" / "index.html").exists()
