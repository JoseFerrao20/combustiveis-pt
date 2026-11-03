"""``combustiveis ingest``: descarrega o histórico do Weekly Oil Bulletin e escreve a camada
landing (Parquet) em ``data/landing``.

``combustiveis ingest --ficheiro historico.xlsx`` usa um ficheiro já descarregado, e
``--idade-maxima 14`` falha se a última semana do boletim tiver mais de 14 dias (a execução
semanal usa-o para dar conta de uma fonte parada).

``combustiveis dgeg``: a fotografia de hoje dos preços de cada posto em Portugal (portal da
DGEG), em ``data/landing/dgeg/AAAA-MM-DD.parquet``.

``combustiveis verificar-dgeg --idade-maxima 8``: falha se a última fotografia da DGEG (semanal,
à segunda-feira) tiver mais de 8 dias, ou se tiver muito menos postos do que a anterior (o
agendamento usa-o para dar conta de uma recolha parada ou de uma resposta incompleta do portal).

``combustiveis mercados``: os preços diários da gasolina e do gasóleo em Nova Iorque, do Brent
e do câmbio do euro (FRED), em ``data/landing/mercados.parquet``, para a previsão de
segunda-feira. ``--ficheiros PASTA`` usa CSV já descarregados (um por série, ``<código>.csv``).

``combustiveis verificar-site --url URL``: confirma que o site publicado tem a página inicial, os
preços de uma fotografia recente e as outras páginas (o ``pages.yml`` corre-o depois do deploy).

``combustiveis site``: os JSON da página inicial do site (``dashboard/app/public/dados/``), a
partir dos Parquet que o dbt exporta (corre-se depois do dbt).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb

from .check import SnapshotError, check_snapshots
from .dgeg import DgegFormatError, read_prices, search_url
from .landing import write_landing, write_markets, write_station_snapshot
from .live import SiteCheckError, check_site
from .markets import SERIES, MarketFormatError, MarketValue, read_series, series_url
from .opendata import export_open_data
from .parse import FormatError, read_bulletin
from .site import export_site
from .source import PAGE_URL, SourceError, fetch, fetch_with_retries, find_history_url

DEFAULT_LANDING = Path("data/landing")
DEFAULT_DGEG = DEFAULT_LANDING / "dgeg"
DEFAULT_MARKETS = DEFAULT_LANDING / "mercados.parquet"
DEFAULT_SITE = Path("dashboard/app/public/dados")


class StaleError(Exception):
    """O boletim não tem semanas recentes: a Comissão deixou de o atualizar, ou o link mudou."""


def ingest(
    file: Path | None, landing: Path, max_age_days: int | None = None, today: date | None = None
) -> int:
    if file is not None:
        data, url = file.read_bytes(), file.resolve().as_uri()
    else:
        url = find_history_url(fetch(PAGE_URL).decode("utf-8", errors="replace"))
        print(f"A descarregar {url}", file=sys.stderr)
        data = fetch(url)
    bulletin = read_bulletin(data)
    if max_age_days is not None:
        age = (today or date.today()) - bulletin.latest_week
        if age > timedelta(days=max_age_days):
            raise StaleError(
                f"A última semana do boletim é {bulletin.latest_week}, há {age.days} dias "
                f"(o máximo é {max_age_days})"
            )
    manifest = write_landing(bulletin, data, url, landing)
    print(
        f"{manifest.prices} preços e {manifest.taxes} impostos, até à semana de "
        f"{manifest.latest_week}, em {landing}/"
    )
    return 0


def snapshot(file: Path | None, directory: Path, day: date | None = None) -> int:
    day = day or date.today()
    if file is not None:
        data = file.read_bytes()
    else:
        url = search_url()
        print(f"A descarregar {url}", file=sys.stderr)
        data = fetch_with_retries(url)
    prices = read_prices(data, day)
    target = write_station_snapshot(prices, directory)
    stations = len({p.station_id for p in prices})
    print(f"{len(prices)} preços de {stations} postos, do dia {day}, em {target}")
    return 0


def markets(files: Path | None, target: Path) -> int:
    values: list[MarketValue] = []
    for series in SERIES:
        if files is not None:
            data = (files / f"{series}.csv").read_bytes()
        else:
            url = series_url(series)
            print(f"A descarregar {url}", file=sys.stderr)
            data = fetch(url)
        values += read_series(data, series)
    write_markets(values, target)
    latest = {series: max(v.day for v in values if v.series == series) for series in SERIES}
    summary = ", ".join(f"{series} até {day}" for series, day in latest.items())
    print(f"{len(values)} valores ({summary}) em {target}")
    return 0


def site(
    stations: Path,
    forecast: Path,
    target: Path,
    pages: Path | None = None,
    warehouse: Path | None = None,
) -> int:
    result = export_site(stations, forecast, target, pages)
    counts = ", ".join(f"{fuel}: {count}" for fuel, count in result.stations.items())
    print(f"Página inicial: postos de {result.snapshot_date} ({counts}) em {target}/")
    if pages is not None:
        print(f"Páginas por concelho: {result.pages} em {pages}/concelho/")
    if pages is not None and warehouse is not None and warehouse.exists():
        files = export_open_data(warehouse, pages, result.snapshot_date)
        summary = ", ".join(f"{f.name} ({f.rows} linhas)" for f in files)
        print(f"Dados abertos em {pages}/dados-abertos/: {summary}")
    return 0


def verify_site(url: str, max_age_days: int, today: date | None = None) -> int:
    result = check_site(url, max_age_days, today or date.today())
    counts = ", ".join(f"{fuel}: {count}" for fuel, count in result.stations.items())
    print(f"Site publicado em ordem: fotografia de {result.snapshot_date} ({counts})")
    return 0


def verify_snapshots(directory: Path, max_age_days: int, today: date | None = None) -> int:
    result = check_snapshots(directory, max_age_days, today or date.today())
    message = f"Última fotografia da DGEG: {result.latest}, com {result.stations} postos"
    if result.previous is not None:
        message += f" ({result.previous_stations} em {result.previous})"
    print(message)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="combustiveis", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("ingest", help="descarrega o boletim e escreve o Parquet")
    command.add_argument("--ficheiro", type=Path, help="usar este .xlsx em vez de descarregar")
    command.add_argument("--destino", type=Path, default=DEFAULT_LANDING)
    command.add_argument(
        "--idade-maxima",
        type=int,
        metavar="DIAS",
        help="falhar se a última semana do boletim tiver mais de DIAS dias",
    )
    command = commands.add_parser("dgeg", help="fotografia de hoje dos preços dos postos (DGEG)")
    command.add_argument("--ficheiro", type=Path, help="usar esta resposta (JSON) do portal")
    command.add_argument("--destino", type=Path, default=DEFAULT_DGEG)
    command.add_argument("--data", type=date.fromisoformat, help="o dia da fotografia (hoje)")
    command = commands.add_parser(
        "verificar-dgeg", help="confirma que o histórico de fotografias da DGEG está em dia"
    )
    command.add_argument("--pasta", type=Path, default=DEFAULT_DGEG)
    command.add_argument(
        "--idade-maxima",
        type=int,
        default=8,
        metavar="DIAS",
        help="falhar se a última fotografia tiver mais de DIAS dias (por omissão, 8)",
    )
    command.add_argument("--hoje", type=date.fromisoformat, help=argparse.SUPPRESS)
    command = commands.add_parser(
        "mercados", help="preços diários dos mercados internacionais e câmbio (FRED)"
    )
    command.add_argument(
        "--ficheiros",
        type=Path,
        help="usar os CSV desta pasta (<código>.csv) em vez de descarregar",
    )
    command.add_argument("--destino", type=Path, default=DEFAULT_MARKETS)
    command = commands.add_parser(
        "verificar-site", help="confirma que o site publicado está como devia (depois do deploy)"
    )
    command.add_argument("--url", required=True, help="o endereço do site publicado")
    command.add_argument(
        "--idade-maxima",
        type=int,
        default=8,
        metavar="DIAS",
        help="falhar se a fotografia da DGEG no site tiver mais de DIAS dias (por omissão, 8)",
    )
    command.add_argument("--hoje", type=date.fromisoformat, help=argparse.SUPPRESS)
    command = commands.add_parser("site", help="os JSON da página inicial do site (depois do dbt)")
    command.add_argument("--postos", type=Path, default=Path("data/stations_latest.parquet"))
    command.add_argument("--previsao", type=Path, default=Path("data/price_forecast.parquet"))
    command.add_argument("--destino", type=Path, default=DEFAULT_SITE)
    command.add_argument(
        "--paginas",
        type=Path,
        default=DEFAULT_SITE.parent,
        help="onde escrever as páginas por concelho (concelho/) e o sitemap.xml",
    )
    command.add_argument(
        "--armazem",
        type=Path,
        default=Path("data/warehouse.duckdb"),
        help="a base de dados do dbt, para os dados abertos (dados-abertos/); sem ela, não há",
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "dgeg":
            return snapshot(args.ficheiro, args.destino, args.data)
        if args.command == "mercados":
            return markets(args.ficheiros, args.destino)
        if args.command == "verificar-site":
            return verify_site(args.url, args.idade_maxima, args.hoje)
        if args.command == "site":
            return site(args.postos, args.previsao, args.destino, args.paginas, args.armazem)
        if args.command == "verificar-dgeg":
            return verify_snapshots(args.pasta, args.idade_maxima, args.hoje)
        return ingest(args.ficheiro, args.destino, args.idade_maxima)
    except (
        SourceError,
        FormatError,
        DgegFormatError,
        StaleError,
        SnapshotError,
        MarketFormatError,
        OSError,
        duckdb.IOException,
        SiteCheckError,
    ) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
