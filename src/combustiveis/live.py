"""A verificação do site publicado, depois de cada deploy (``combustiveis verificar-site``).

Abre o site como um visitante e confirma o que tem de estar lá: a página inicial (a de
``dashboard/app/``), os preços em ``dados/`` com uma fotografia recente e com postos, o JSON do
primeiro combustível com os postos que o resumo anuncia, as outras páginas e os seus dados, o
service worker, o manifesto, a página dos concelhos e o ``sitemap.xml``. Junta todos os
problemas numa só mensagem, para o email do GitHub dizer tudo.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from .source import fetch_with_retries


class SiteCheckError(Exception):
    """O site publicado não está como devia."""


@dataclass(frozen=True)
class SiteCheck:
    snapshot_date: date
    stations: dict[str, int]


def _text(fetch: Callable[[str], bytes], url: str, problems: list[str]) -> str | None:
    try:
        return fetch(url).decode("utf-8")
    except OSError as exc:  # HTTPError, URLError e tempo esgotado são OSError
        problems.append(f"{url}: {exc}")
        return None


def check_site(
    base_url: str,
    max_age_days: int,
    today: date,
    fetch: Callable[[str], bytes] | None = None,
) -> SiteCheck:
    fetch = fetch or fetch_with_retries
    base = base_url if base_url.endswith("/") else base_url + "/"
    problems: list[str] = []

    home = _text(fetch, base, problems)
    if home is not None and ('id="app"' not in home or "/inicio/" not in home):
        problems.append(
            f"{base}: não é a página inicial (faltam o #app ou os ficheiros de inicio/)"
        )

    summary: dict[str, Any] = {}
    raw = _text(fetch, base + "dados/resumo.json", problems)
    snapshot = date.min
    if raw is not None:
        try:
            summary = json.loads(raw)
            snapshot = date.fromisoformat(summary["snapshot_date"])
        except (ValueError, KeyError, TypeError) as exc:
            problems.append(f"dados/resumo.json inválido: {exc}")
            summary = {}
    if summary:
        age = (today - snapshot).days
        if age > max_age_days:
            problems.append(
                f"a fotografia da DGEG no site é de {snapshot}, há {age} dias "
                f"(máximo: {max_age_days})"
            )
        fuels = summary.get("fuels") or []
        if not fuels:
            problems.append("dados/resumo.json não tem combustíveis")
        for fuel in fuels:
            if fuel.get("stations", 0) <= 0:
                problems.append(f"{fuel.get('fuel')}: sem postos no resumo")
        if fuels:
            first = fuels[0]
            raw_fuel = _text(fetch, base + f"dados/postos-{first['fuel']}.json", problems)
            if raw_fuel is not None:
                try:
                    count = len(json.loads(raw_fuel)["stations"])
                except (ValueError, KeyError, TypeError) as exc:
                    problems.append(f"dados/postos-{first['fuel']}.json inválido: {exc}")
                else:
                    if count != first.get("stations"):
                        problems.append(
                            f"dados/postos-{first['fuel']}.json tem {count} postos, "
                            f"e o resumo diz {first.get('stations')}"
                        )

    page = _text(fetch, base + "resumo/", problems)
    if page is not None and "Resumo e estatísticas" not in page:
        problems.append(f"{base}resumo/: não tem o título da página")
    tracked = _text(fetch, base + "dados/acompanhados.json", problems)
    if tracked is not None:
        try:
            if not json.loads(tracked)["history"]:
                problems.append("dados/acompanhados.json sem postos acompanhados")
        except (ValueError, KeyError, TypeError) as exc:
            problems.append(f"dados/acompanhados.json inválido: {exc}")
    concelhos = _text(fetch, base + "concelho/", problems)
    if concelhos is not None and "Preços por concelho" not in concelhos:
        problems.append(f"{base}concelho/: não é a página dos concelhos")
    islands = _text(fetch, base + "dados/ilhas.json", problems)
    if islands is not None:
        try:
            if not isinstance(json.loads(islands)["rows"], list):
                raise TypeError("rows não é uma lista")
        except (ValueError, KeyError, TypeError) as exc:
            problems.append(f"dados/ilhas.json inválido: {exc}")
    page = _text(fetch, base + "ilhas/", problems)
    if page is not None and "Açores e Madeira" not in page:
        problems.append(f"{base}ilhas/: não tem o título da página")
    bulletin = _text(fetch, base + "dados/boletim.json", problems)
    if bulletin is not None:
        try:
            if not json.loads(bulletin)["portugal"]["rows"]:
                problems.append("dados/boletim.json sem as semanas de Portugal")
        except (ValueError, KeyError, TypeError) as exc:
            problems.append(f"dados/boletim.json inválido: {exc}")
    page = _text(fetch, base + "analises/impostos/", problems)
    if page is not None and "Quanto do preço é imposto?" not in page:
        problems.append(f"{base}analises/impostos/: não tem o título da página")
    abertos = _text(fetch, base + "dados-abertos/", problems)
    if abertos is not None and "postos-historico.csv.gz" not in abertos:
        problems.append(f"{base}dados-abertos/: sem o link para o histórico dos postos")
    sitemap = _text(fetch, base + "sitemap.xml", problems)
    if sitemap is not None and "/concelho/" not in sitemap:
        problems.append("sitemap.xml sem as páginas por concelho")
    for path in ("sw.js", "manifest.webmanifest"):
        _text(fetch, base + path, problems)

    if problems:
        raise SiteCheckError("O site publicado tem problemas:\n- " + "\n- ".join(problems))
    return SiteCheck(
        snapshot_date=snapshot,
        stations={fuel["fuel"]: fuel["stations"] for fuel in summary["fuels"]},
    )
