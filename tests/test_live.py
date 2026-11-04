import io
import json
import urllib.error
from collections.abc import Callable
from datetime import date

import pytest

from combustiveis import __main__ as cli
from combustiveis import live
from combustiveis.live import SiteCheckError, check_site

BASE = "https://exemplo.pt/combustiveis-pt/"
TODAY = date(2026, 11, 3)


def _site(**changes: bytes | None) -> dict[str, bytes | None]:
    """Um site publicado em ordem; `changes` troca (ou tira, com None) ficheiros."""
    files: dict[str, bytes | None] = {
        "": b'<div id="app"></div><script src="/combustiveis-pt/inicio/index.js"></script>',
        "dados/resumo.json": json.dumps(
            {
                "snapshot_date": "2026-11-02",
                "fuels": [
                    {"fuel": "gasolina_95", "stations": 2},
                    {"fuel": "gasoleo", "stations": 1},
                ],
            }
        ).encode(),
        "dados/postos-gasolina_95.json": json.dumps({"stations": [[1], [2]]}).encode(),
        "resumo/": "<h1>Resumo e estatísticas</h1>".encode(),
        "dados/acompanhados.json": b'{"history": [{"station_id": 1}], "competitors": []}',
        "dados/ilhas.json": b'{"rows": []}',
        "ilhas/": "<title>Açores e Madeira | Combustíveis em Portugal</title>".encode(),
        "concelho/": "<h1>Preços por concelho</h1>".encode(),
        "dados-abertos/": b'<a href="postos-historico.csv.gz" download>',
        "sitemap.xml": b"<loc>https://exemplo.pt/combustiveis-pt/concelho/braga/</loc>",
        "sw.js": b"self.addEventListener",
        "manifest.webmanifest": b"{}",
    }
    files.update(changes)
    return files


def _fetch(files: dict[str, bytes | None]) -> Callable[[str], bytes]:
    def fetch(url: str) -> bytes:
        content = files.get(url.removeprefix(BASE))
        if content is None:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO())  # type: ignore[arg-type]
        return content

    return fetch


def test_a_good_site() -> None:
    result = check_site(BASE, 8, TODAY, _fetch(_site()))
    assert result.snapshot_date == date(2026, 11, 2)
    assert result.stations == {"gasolina_95": 2, "gasoleo": 1}


def test_all_problems_in_one_message() -> None:
    files = _site(
        **{
            "": b"<html>Evidence</html>",
            "dados/postos-gasolina_95.json": json.dumps({"stations": [[1]]}).encode(),
            "sw.js": None,
            "concelho/": b"<h1>Outra</h1>",
            "dados-abertos/": b"<h1>Outra</h1>",
            "sitemap.xml": b"<urlset></urlset>",
            "dados/acompanhados.json": b'{"history": [], "competitors": []}',
        }
    )
    with pytest.raises(SiteCheckError) as error:
        check_site(BASE, 8, TODAY, _fetch(files))
    message = str(error.value)
    assert "não é a página inicial" in message
    assert "tem 1 postos, e o resumo diz 2" in message
    assert "sw.js: HTTP Error 404" in message
    assert "concelho/: não é a página dos concelhos" in message
    assert "dados-abertos/: sem o link" in message
    assert "sitemap.xml sem as páginas por concelho" in message
    assert "dados/acompanhados.json sem postos acompanhados" in message


def test_old_snapshot_and_empty_fuel() -> None:
    summary = {"snapshot_date": "2026-10-19", "fuels": [{"fuel": "gasolina_95", "stations": 0}]}
    files = _site(
        **{
            "dados/resumo.json": json.dumps(summary).encode(),
            "dados/postos-gasolina_95.json": json.dumps({"stations": []}).encode(),
        }
    )
    with pytest.raises(SiteCheckError) as error:
        check_site(BASE.rstrip("/"), 8, TODAY, _fetch(files))
    assert "é de 2026-10-19, há 15 dias (máximo: 8)" in str(error.value)
    assert "gasolina_95: sem postos no resumo" in str(error.value)


def test_broken_json() -> None:
    files = _site(
        **{
            "dados/resumo.json": b"{",
            "resumo/": b"<h1>Outra coisa</h1>",
            "dados/acompanhados.json": b"{",
            "dados/ilhas.json": b"[]",
            "ilhas/": b"<h1>Outra</h1>",
        }
    )
    with pytest.raises(SiteCheckError) as error:
        check_site(BASE, 8, TODAY, _fetch(files))
    assert "dados/resumo.json inválido" in str(error.value)
    assert "resumo/: não tem o título" in str(error.value)
    assert "dados/acompanhados.json inválido" in str(error.value)
    assert "dados/ilhas.json inválido" in str(error.value)
    assert "ilhas/: não tem o título" in str(error.value)


def test_no_fuels_and_broken_fuel_file() -> None:
    files = _site(**{"dados/resumo.json": b'{"snapshot_date": "2026-11-02", "fuels": []}'})
    with pytest.raises(SiteCheckError, match="não tem combustíveis"):
        check_site(BASE, 8, TODAY, _fetch(files))
    files = _site(**{"dados/postos-gasolina_95.json": b"[]"})
    with pytest.raises(SiteCheckError, match=r"postos-gasolina_95\.json inválido"):
        check_site(BASE, 8, TODAY, _fetch(files))


def test_command_line(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(live, "fetch_with_retries", _fetch(_site()))
    args = ["verificar-site", "--url", BASE, "--hoje", "2026-11-03"]
    assert cli.main(args) == 0
    assert "Site publicado em ordem: fotografia de 2026-11-02 (gasolina_95: 2" in (
        capsys.readouterr().out
    )
    assert cli.main([*args[:-1], "2026-11-20"]) == 1
    assert "erro: O site publicado tem problemas" in capsys.readouterr().err
