"""As páginas por concelho do site (``concelho/<nome>/``), estáticas, para quem procura no Google.

Uma página por concelho, com os postos mais baratos de cada combustível (com a data e a hora de
cada preço, como pedem os termos da DGEG) e as médias do concelho, do distrito e do país; uma
página com todos os concelhos, por distrito; e o ``sitemap.xml`` do site. São HTML simples, sem
JavaScript além do tema (o estilo está em ``dashboard/static/concelho/estilo.css``), e o botão
"Ver no mapa" abre a página inicial já no concelho
(``?concelho=``) ou no posto (``?posto=``).
"""

from __future__ import annotations

import html
import re
import shutil
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

import duckdb

SITE_URL = "https://joseferrao20.github.io/combustiveis-pt/"
# Quantos postos de cada combustível aparecem em cada página.
TOP = 10
# As páginas do Evidence, para o sitemap (a inicial e as por concelho juntam-se a estas).
EVIDENCE_PAGES = (
    "resumo/",
    "acompanhados/",
    "analises/",
    "analises/impostos/",
    "analises/previsao/",
    "analises/comparacao/",
    "analises/metodo/",
)
FUEL_ORDER = ("gasolina_95", "gasolina_98", "gasoleo", "gpl")
_SMALL_WORDS = {"de", "da", "do", "das", "dos", "e", "a", "o", "em", "na", "no"}
_ROMAN = re.compile(r"^(i{1,3}|iv|v|vi{1,3}|ix|x)$")
_VOWELS = re.compile(r"[aeiouáéíóúâêôãõà]")
_WORD = re.compile(r"[^\s.\-/()]+")


@dataclass(frozen=True)
class Station:
    district: str
    municipality: str
    fuel: str
    fuel_name: str
    station_id: int
    station_name: str
    brand: str
    locality: str | None
    price: float
    updated_at: datetime
    stations: int
    municipality_avg: float
    district_avg: float
    country_avg: float


def slug(text: str) -> str:
    """'Vila Nova de Gaia' -> 'vila-nova-de-gaia' (sem acentos)."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def tidy(text: str) -> str:
    """Os nomes da DGEG sem as maiúsculas todas, como na página inicial (MapaPostos.svelte)."""
    if not text:
        return ""
    all_caps = not re.search(r"[a-zà-ÿ]", text)
    first = True

    def word(match: re.Match[str]) -> str:
        nonlocal first
        original = match.group(0)
        is_first, first = first, False
        if not all_caps and (re.search(r"[a-zà-ÿ]", original) or len(original) < 4):
            return original
        lower = original.lower()
        if not is_first and lower in _SMALL_WORDS:
            return lower
        if _ROMAN.match(lower) or (len(lower) <= 3 and not _VOWELS.search(lower)):
            return lower.upper()
        return lower[0].upper() + lower[1:]

    return _WORD.sub(word, text)


def of_district(name: str) -> str:
    """'distrito do Porto', 'distrito da Guarda', 'distrito de Braga'."""
    article = {"Porto": "do", "Guarda": "da"}.get(name, "de")
    return f"distrito {article} {name}"


def _euros(value: float) -> str:
    return f"{value:.3f}".replace(".", ",") + " €"


def _brand(name: str) -> str:
    return "Sem marca" if name == "Genérico" else tidy(name)


def read_stations(stations: Path) -> list[Station]:
    """Os postos mais baratos de cada concelho e combustível, com as médias para comparar."""
    rows = (
        duckdb.connect()
        .execute(
            f"""
            select
                district, municipality, fuel, fuel_name, station_id, station_name, brand,
                locality, price, updated_at,
                count(*) over (partition by municipality, fuel) as stations,
                avg(price) over (partition by municipality, fuel) as municipality_avg,
                avg(price) over (partition by district, fuel) as district_avg,
                avg(price) over (partition by fuel) as country_avg
            from read_parquet(?)
            where is_current and district is not null and municipality is not null
            qualify row_number() over (
                partition by municipality, fuel order by price, station_name
            ) <= {TOP}
            order by district, municipality, fuel, price, station_name
            """,  # noqa: S608 (o TOP é uma constante)
            [str(stations)],
        )
        .fetchall()
    )
    return [Station(*row) for row in rows]


_THEME = (
    "<script>try{var t=localStorage.getItem('evidence-theme');"
    "document.documentElement.dataset.theme=t==='light'||t==='dark'?t:"
    "(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light')}catch(e){}</script>"
)
_THEME_BUTTON = (
    "<script>(function(){var b=document.querySelector('.tema'),h=document.documentElement;"
    "function m(){var d=h.dataset.theme==='dark';b.textContent=d?'☀':'☾';"
    "b.setAttribute('aria-label',d?'Mudar para o tema claro':'Mudar para o tema escuro')}"
    "b.addEventListener('click',function(){h.dataset.theme=h.dataset.theme==='dark'?'light':'dark';"
    "try{localStorage.setItem('evidence-theme',h.dataset.theme)}catch(e){}m()});m()})()</script>"
)


def _page(title: str, description: str, path: str, root: str, body: str) -> str:
    esc = html.escape
    return f"""<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{SITE_URL}{path}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="{SITE_URL}og.png">
<meta name="theme-color" content="#2563eb">
<link rel="icon" href="{root}favicon.ico" sizes="32x32">
<link rel="icon" href="{root}icon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{root}concelho/estilo.css">
{_THEME}
</head>
<body>
<header class="cabecalho">
<a class="marca" href="{root}"><img src="{root}icon.svg" alt="" width="24" height="24">\
<span>Combustíveis em Portugal</span></a>
<nav aria-label="Páginas do site"><a href="{root}">Início</a><a href="{root}resumo/">Resumo</a>\
<a href="{root}acompanhados/">Postos acompanhados</a><a href="{root}analises/">Análises</a></nav>
<button type="button" class="tema" aria-label="Mudar o tema">☾</button>
</header>
<main>
{body}
<footer>
<p>Preços comunicados pelos postos à Direção-Geral de Energia e Geologia
(<a href="https://precoscombustiveis.dgeg.gov.pt">precoscombustiveis.dgeg.gov.pt</a>); cada preço
tem a data e a hora da última atualização. As médias usam só os preços dos últimos 30 dias.</p>
<p><a href="{root}concelho/">Preços por concelho</a> ·
<a href="https://github.com/JoseFerrao20/combustiveis-pt">Código no GitHub</a></p>
</footer>
</main>
{_THEME_BUTTON}
</body>
</html>
"""


def _municipality_page(
    district: str,
    municipality: str,
    rows: list[Station],
    neighbours: list[tuple[str, str]],
    snapshot: date,
) -> str:
    esc = html.escape
    root = "../../"
    by_fuel: dict[str, list[Station]] = defaultdict(list)
    for row in rows:
        by_fuel[row.fuel].append(row)
    fuels = sorted(by_fuel, key=lambda f: FUEL_ORDER.index(f) if f in FUEL_ORDER else 99)
    total = max(r.stations for r in rows)
    # Para o Google: a gasolina 95 e o gasóleo, os mais procurados (ou os que houver).
    main_fuels = [f for f in ("gasolina_95", "gasoleo") if f in by_fuel] or fuels[:2]
    cheapest = "; ".join(
        f"{by_fuel[f][0].fuel_name} a partir de {_euros(by_fuel[f][0].price)}" for f in main_fuels
    )
    sections = []
    for fuel in fuels:
        fuel_rows = by_fuel[fuel]
        first = fuel_rows[0]
        lines = "\n".join(
            f'<tr><td>{esc(tidy(r.station_name))}<br><span class="suave">'
            f"{esc(_brand(r.brand))}{' · ' + esc(r.locality) if r.locality else ''}</span></td>"
            f'<td class="num"><strong>{_euros(r.price)}</strong><br>'
            f'<span class="suave">{r.updated_at:%d/%m/%Y %H:%M}</span></td>'
            f'<td><a href="{root}?posto={r.station_id}&amp;combustivel={fuel}" '
            f'aria-label="Mapa: {esc(tidy(r.station_name))}">Mapa</a></td></tr>'
            for r in fuel_rows
        )
        sections.append(
            f"""<section>
<h2>{esc(first.fuel_name)}</h2>
<p>Média em {esc(municipality)}: <strong>{_euros(first.municipality_avg)}</strong>
({first.stations} {"posto" if first.stations == 1 else "postos"}) ·
{esc(of_district(district))}: {_euros(first.district_avg)} ·
continente: {_euros(first.country_avg)}</p>
<table>
<thead><tr><th>Posto</th><th class="num">Preço e atualização</th>\
<th><span class="sr-only">No mapa</span></th></tr></thead>
<tbody>
{lines}
</tbody>
</table>
</section>"""
        )
    others = ", ".join(
        f'<a href="{root}concelho/{other_slug}/">{esc(name)}</a>' for name, other_slug in neighbours
    )
    body = f"""<p class="caminho"><a href="{root}concelho/">Preços por concelho</a> &rsaquo;
{esc(district)}</p>
<h1>Combustível mais barato em {esc(municipality)}</h1>
<p>Os {TOP} postos mais baratos de cada combustível em {esc(municipality)} ({total}
{"posto" if total == 1 else "postos"} com o preço atualizado), segundo a fotografia de
{snapshot:%d/%m/%Y} da DGEG.</p>
<p><a class="botao" href="{root}?concelho={quote(municipality)}">Ver todos no mapa</a></p>
{"".join(sections)}
<h2>Outros concelhos do {esc(of_district(district))}</h2>
<p>{others}</p>"""
    title = f"Combustível mais barato em {municipality}"
    description = (
        f"Os postos de combustível mais baratos em {municipality} ({district}): {cheapest}. "
        f"Preços da DGEG de {snapshot:%d/%m/%Y}, com a data e a hora de cada um."
    )
    return _page(title, description, f"concelho/{slug(municipality)}/", root, body)


def write_pages(stations: Path, target: Path, snapshot: date) -> int:
    """Escreve as páginas em ``target/concelho/`` e o ``target/sitemap.xml``; devolve quantas."""
    rows = read_stations(stations)
    groups: dict[tuple[str, str], list[Station]] = defaultdict(list)
    for row in rows:
        groups[(row.district, row.municipality)].append(row)
    # Um nome repetido em dois distritos fica com o distrito no endereço.
    counts: dict[str, int] = defaultdict(int)
    for _, municipality in groups:
        counts[slug(municipality)] += 1
    slugs = {
        key: slug(key[1]) if counts[slug(key[1])] == 1 else f"{slug(key[1])}-{slug(key[0])}"
        for key in groups
    }
    by_district: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for (district, municipality), page_slug in sorted(slugs.items()):
        by_district[district].append((municipality, page_slug))

    # A pasta é toda gerada: começa vazia, para não ficarem páginas de concelhos sem postos (o
    # estilo está em dashboard/static/concelho/, à parte).
    folder = target / "concelho"
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    for (district, municipality), page_slug in slugs.items():
        neighbours = [n for n in by_district[district] if n[0] != municipality]
        page = folder / page_slug
        page.mkdir(exist_ok=True)
        (page / "index.html").write_text(
            _municipality_page(district, municipality, groups[(district, municipality)],
                               neighbours, snapshot),
            "utf-8",
        )  # fmt: skip

    esc = html.escape
    lists = "\n".join(
        f'<h2>{esc(district)}</h2>\n<ul class="lista">'
        + "".join(f'<li><a href="{s}/">{esc(name)}</a></li>' for name, s in items)
        + "</ul>"
        for district, items in sorted(by_district.items())
    )
    body = f"""<h1>Preços por concelho</h1>
<p>Os postos mais baratos de cada concelho de Portugal continental, com a fotografia de
{snapshot:%d/%m/%Y} da DGEG. Para os que estão perto de si, use o
<a href="../">mapa da página inicial</a>.</p>
{lists}"""
    (folder / "index.html").write_text(
        _page(
            "Preços dos combustíveis por concelho",
            "O combustível mais barato em cada concelho de Portugal continental, com os preços "
            "da DGEG.",
            "concelho/",
            "../",
            body,
        ),
        "utf-8",
    )
    paths = ["", *EVIDENCE_PAGES, "concelho/", *(f"concelho/{s}/" for s in sorted(slugs.values()))]
    urls = "\n".join(
        f"<url><loc>{SITE_URL}{path}</loc><lastmod>{snapshot:%Y-%m-%d}</lastmod></url>"
        for path in paths
    )
    (target / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n</urlset>\n",
        "utf-8",
    )
    return len(slugs)
