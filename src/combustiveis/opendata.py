"""Os dados abertos do site (``dados-abertos/``): os dados do projeto em CSV, para quem os usar.

A DGEG só mostra o preço em vigor; o histórico de cada posto existe porque este projeto tira uma
fotografia por semana (ADR 0003), e por isso vale a pena publicá-lo. Saem do armazém do dbt
(``data/warehouse.duckdb``):

- ``postos-historico.csv.gz``: todas as fotografias da DGEG (``fct_station_prices``);
- ``postos-ultima-fotografia.csv``: só a última, sem comprimir;
- ``boletim-europeu.csv.gz``: o Weekly Oil Bulletin desde 2005, com os impostos
  (``fct_fuel_prices``);
- ``ilhas-precos-maximos.csv``: os preços máximos dos Açores e da Madeira, despacho a despacho
  (``stg_ilhas__max_prices``; ADR 0007), quando o armazém os tem.

E uma página (``dados-abertos/index.html``) com as colunas, as fontes e como citar.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb

from .pages import _page

STATIONS_QUERY = """
    select
        prices.snapshot_date, prices.station_id, prices.station_name, prices.brand,
        prices.station_type, prices.district, prices.municipality, prices.locality,
        prices.address, prices.postal_code, prices.latitude, prices.longitude, prices.fuel,
        fuels.name as fuel_name, prices.price, prices.updated_at, prices.is_current
    from fct_station_prices as prices
    left join dgeg_fuels as fuels using (fuel)
"""
BULLETIN_QUERY = """
    select
        prices.week, prices.country_code, countries.name as country, prices.product,
        products.name as product_name, products.unit,
        -- Os valores do boletim têm 2 casas decimais; as contas, mais. Arredonda-se para o
        -- ficheiro ficar pequeno, sem perder nada que o boletim diga.
        round(prices.price_with_tax, 2) as price_with_tax,
        round(prices.price_without_tax, 2) as price_without_tax,
        round(prices.excise_and_other_taxes, 2) as excise_and_other_taxes,
        round(prices.vat_amount, 2) as vat_amount,
        round(prices.vat_rate, 2) as vat_rate,
        round(prices.taxes_total, 2) as taxes_total,
        round(prices.tax_share, 4) as tax_share,
        countries.euro_since
    from fct_fuel_prices as prices
    left join countries using (country_code)
    left join products using (product)
    order by prices.week, prices.country_code, prices.product
"""

ISLANDS_QUERY = """
    select region, fuel, valid_from, price, act, published, source_url
    from stg_ilhas__max_prices
    order by region, fuel, valid_from
"""

# As colunas de cada ficheiro, para a página (nome, descrição).
STATION_COLUMNS = (
    ("snapshot_date", "dia da fotografia (diária de 28/10 a 2/11/2026, depois às segundas-feiras)"),
    ("station_id", "id do posto na DGEG"),
    ("station_name, brand, station_type", "nome, marca e tipo do posto, como na DGEG"),
    ("district, municipality, locality, address, postal_code", "onde fica"),
    ("latitude, longitude", "coordenadas (WGS 84), quando a DGEG as tem"),
    ("fuel, fuel_name", "o combustível (código e nome)"),
    ("price", "preço em euros por litro, como o posto o comunicou"),
    ("updated_at", "data e hora (de Lisboa) em que o posto comunicou o preço"),
    ("is_current", "o preço foi atualizado nos 30 dias antes da fotografia"),
)
BULLETIN_COLUMNS = (
    ("week", "segunda-feira da semana a que os preços se referem"),
    ("country_code, country", "o país (ou a média da UE e da zona euro)"),
    ("product, product_name, unit", "o produto e a unidade dos valores (1000 L ou tonelada)"),
    ("price_with_tax, price_without_tax", "preço com e sem impostos"),
    ("excise_and_other_taxes, vat_amount, vat_rate, taxes_total, tax_share",
     "ISP e outros impostos, IVA (valor e taxa), total de impostos e a parte do preço"),
    ("euro_since",
     "desde quando o país usa o euro: antes disso, os valores estão na moeda nacional"),
)  # fmt: skip

ISLAND_COLUMNS = (
    ("region", "acores ou madeira"),
    ("fuel", "gasolina_95 (gasolina sem chumbo 95) ou gasoleo (gasóleo rodoviário)"),
    ("valid_from", "dia em que o preço máximo entra em vigor"),
    ("price", "preço máximo de venda ao público, em euros por litro, com IVA"),
    ("act, published, source_url", "o despacho, o dia em que foi publicado e o PDF"),
)


@dataclass(frozen=True)
class OpenFile:
    name: str
    rows: int
    size: int


def _copy(db: duckdb.DuckDBPyConnection, query: str, path: Path) -> int:
    options = "(header, delimiter ',', compression gzip)" if path.suffix == ".gz" else "(header)"
    db.execute(f"copy ({query}) to '{path}' {options}")
    count = db.execute(f"select count(*) from ({query})").fetchall()[0][0]  # noqa: S608
    return int(count)


def export_open_data(warehouse: Path, target: Path, snapshot: date) -> list[OpenFile]:
    """Escreve os ficheiros e a página em ``target/dados-abertos/``; devolve os ficheiros."""
    folder = target / "dados-abertos"
    folder.mkdir(parents=True, exist_ok=True)
    db = duckdb.connect(str(warehouse), read_only=True)
    latest = (
        f"{STATIONS_QUERY} where prices.snapshot_date = "  # noqa: S608 (consultas fixas)
        "(select max(snapshot_date) from fct_station_prices)"
    )
    queries = {
        "postos-historico.csv.gz": f"{STATIONS_QUERY} order by snapshot_date, station_id, fuel",
        "postos-ultima-fotografia.csv": f"{latest} order by station_id, fuel",
        "boletim-europeu.csv.gz": BULLETIN_QUERY,
    }
    tables = {
        row[0] for row in db.execute("select table_name from information_schema.tables").fetchall()
    }
    if "stg_ilhas__max_prices" in tables:
        queries["ilhas-precos-maximos.csv"] = ISLANDS_QUERY
    files = []
    for name, query in queries.items():
        rows = _copy(db, query, folder / name)
        files.append(OpenFile(name, rows, (folder / name).stat().st_size))
    weeks = db.execute("select min(week), max(week) from fct_fuel_prices").fetchall()[0]
    (folder / "index.html").write_text(_index(files, snapshot, weeks[0], weeks[1]), "utf-8")
    return files


def _size(size: int) -> str:
    if size >= 1_000_000:
        return f"{size / 1_000_000:.1f} MB".replace(".", ",")
    return f"{max(1, round(size / 1000))} KB"


def _columns(columns: tuple[tuple[str, str], ...]) -> str:
    esc = html.escape
    rows = "".join(f"<tr><td><code>{esc(c)}</code></td><td>{esc(d)}</td></tr>" for c, d in columns)
    head = "<thead><tr><th>Colunas</th><th>O que são</th></tr></thead>"
    return f"<table>{head}<tbody>{rows}</tbody></table>"


def _link(by_name: dict[str, OpenFile], name: str, text: str) -> str:
    f = by_name[name]
    return (
        f'<a href="{name}" download>{text}</a> '
        f'<span class="suave">({f.rows:,} linhas, {_size(f.size)})</span>'.replace(",", " ")
    )


def _islands(by_name: dict[str, OpenFile]) -> str:
    if "ilhas-precos-maximos.csv" not in by_name:
        return ""
    link = _link(by_name, "ilhas-precos-maximos.csv", "Todos os despachos desde 2025")
    return f"""<h2>Açores e Madeira (preços máximos)</h2>
<p>A DGEG só tem os postos do continente. Nas regiões autónomas, o governo regional fixa o preço
máximo da gasolina 95 e do gasóleo: todos os meses nos Açores (Jornal Oficial, I série) e todas
as semanas na Madeira (JORAM, II série). Este projeto lê os despachos em PDF
(<a href="../ilhas/">ver no site</a>).</p>
<ul>
<li>{link}</li>
</ul>
{_columns(ISLAND_COLUMNS)}
<p>Fontes: Jornal Oficial da Região Autónoma dos Açores
(<a href="https://jo.azores.gov.pt">jo.azores.gov.pt</a>) e Jornal Oficial da Região Autónoma
da Madeira (<a href="https://joram.madeira.gov.pt">joram.madeira.gov.pt</a>). Cada linha tem o
endereço do despacho.</p>
"""


def _index(files: list[OpenFile], snapshot: date, first_week: date, last_week: date) -> str:
    by_name = {f.name: f for f in files}

    def link(name: str, text: str) -> str:
        return _link(by_name, name, text)

    body = f"""<h1>Dados abertos</h1>
<p>Os dados que o site usa, em CSV (separados por vírgulas, com cabeçalho, em UTF-8), para
quem os quiser analisar. Atualizados com a fotografia de {snapshot:%d/%m/%Y}.</p>

<h2>Preços de cada posto (DGEG)</h2>
<p>A DGEG só mostra o preço em vigor: o histórico existe porque este projeto tira uma fotografia
dos preços de cada posto de Portugal continental (diária de 28/10 a 2/11/2026, depois às
segundas-feiras).</p>
<ul>
<li>{link("postos-historico.csv.gz", "Todas as fotografias")} (comprimido com gzip)</li>
<li>{link("postos-ultima-fotografia.csv", "Só a última fotografia")}</li>
</ul>
{_columns(STATION_COLUMNS)}
<p>Fonte: Direção-Geral de Energia e Geologia, Preços dos Combustíveis Online
(<a href="https://precoscombustiveis.dgeg.gov.pt">precoscombustiveis.dgeg.gov.pt</a>). Os preços
são os que os postos comunicam, sem alterações; ao usar os dados, indique a fonte e a data e hora
de atualização de cada preço.</p>

<h2>Weekly Oil Bulletin (Comissão Europeia)</h2>
<p>Os preços semanais dos combustíveis em cada país da UE, com e sem impostos, de
{first_week:%d/%m/%Y} a {last_week:%d/%m/%Y}, com a divisão do preço em produto, ISP e outros
impostos e IVA feita por este projeto (<a href="../analises/metodo/">como se calcula</a>).</p>
<ul>
<li>{link("boletim-europeu.csv.gz", "Todos os países e semanas")} (comprimido com gzip)</li>
</ul>
{_columns(BULLETIN_COLUMNS)}
<p>Fonte: Comissão Europeia, Weekly Oil Bulletin
(<a href="https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en">energy.ec.europa.eu</a>),
reutilizável com a indicação da fonte.</p>

{_islands(by_name)}
<h2>Como citar</h2>
<p>"Combustíveis em Portugal (José Ferrão), a partir de dados da DGEG e da Comissão Europeia",
com o endereço desta página. O código que gera os dados está no
<a href="https://github.com/JoseFerrao20/combustiveis-pt">GitHub</a>.</p>"""
    return _page(
        "Dados abertos: preços dos combustíveis em Portugal",
        "O histórico do preço de cada posto de combustível em Portugal (DGEG) e o Weekly Oil "
        "Bulletin desde 2005, em CSV.",
        "dados-abertos/",
        "../",
        body,
    )
