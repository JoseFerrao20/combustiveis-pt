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

``combustiveis telegram [--enviar]``: os avisos de segunda-feira pelo Telegram (inscrições em
``TELEGRAM_SUBSCRIPTIONS`` e o token em ``TELEGRAM_BOT_TOKEN``; sem ``--enviar``, só mostra).

``combustiveis ilhas``: os preços máximos dos Açores e da Madeira, lidos dos despachos em PDF
publicados desde a última execução (histórico em ``data/landing/ilhas/precos.csv``).
``combustiveis verificar-ilhas`` falha se faltar o preço da semana (Madeira) ou do mês (Açores).

``combustiveis site``: os JSON da página inicial do site (``dashboard/app/public/dados/``), a
partir dos Parquet que o dbt exporta (corre-se depois do dbt).
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb

from . import ilhas as islands
from .check import SnapshotError, check_snapshots
from .dgeg import DgegFormatError, read_prices, search_url
from .landing import write_landing, write_markets, write_station_snapshot
from .live import SiteCheckError, check_site
from .markets import SERIES, MarketFormatError, MarketValue, read_series, series_url
from .opendata import export_open_data
from .parse import FormatError, read_bulletin
from .site import (
    export_analyses,
    export_history,
    export_islands,
    export_site,
    export_tracked,
)
from .source import PAGE_URL, SourceError, fetch, fetch_with_retries, find_history_url
from .telegram import TelegramError, build_message, read_data, send, subscriptions_from_env

DEFAULT_LANDING = Path("data/landing")
DEFAULT_DGEG = DEFAULT_LANDING / "dgeg"
DEFAULT_MARKETS = DEFAULT_LANDING / "mercados.parquet"
DEFAULT_ISLANDS = DEFAULT_LANDING / "ilhas"
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
    extras: tuple[Path, Path, Path] | None = None,
    islands_prices: Path | None = None,
    bulletin: Path | None = None,
) -> int:
    result = export_site(stations, forecast, target, pages)
    if bulletin is not None and bulletin.exists():
        weeks = export_analyses(bulletin, forecast, DEFAULT_LANDING / "manifest.json", target)
        print(f"Análises: {weeks} semanas do boletim em {target}/boletim.json e previsao.json")
    if islands_prices is not None and islands_prices.exists():
        count = export_islands(islands_prices, target)
        print(f"Açores e Madeira: {count} preços máximos em {target}/ilhas.json")
    # As páginas do resumo e dos postos acompanhados (app/resumo/, app/acompanhados/).
    if extras is not None:
        daily, tracked, competitors = extras
        if daily.exists():
            print(f"Evolução: {export_history(daily, target)} linhas em {target}/evolucao.json")
        if tracked.exists() and competitors.exists():
            count = export_tracked(tracked, competitors, target)
            print(f"Postos acompanhados: {count} linhas em {target}/acompanhados.json")
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


def telegram(stations: Path, forecast: Path, deliver: bool) -> int:
    subscriptions = subscriptions_from_env()
    if not subscriptions:
        print("Ninguém inscrito nos avisos (TELEGRAM_SUBSCRIPTIONS vazio): nada a enviar.")
        return 0
    snapshot, rows, summary = read_data(stations, forecast)
    messages = [(s, build_message(s, snapshot, rows, summary)) for s in subscriptions]
    if not deliver:
        for subscription, text in messages:
            print(f"--- para {subscription.chat_id}\n{text}\n")
        return 0
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("Sem TELEGRAM_BOT_TOKEN: nada enviado.")
        return 0
    print(f"Avisos enviados: {send(token, messages)}")
    return 0


def update_islands(directory: Path, since: date, today: date | None = None) -> int:
    history_path, state_path = directory / "precos.csv", directory / "estado.json"
    state = islands.read_state(state_path, since)
    result = islands.update(state, today or date.today())
    history = islands.write_history(
        history_path, islands.read_history(history_path) + result.prices
    )
    islands.write_state(state_path, result.state)
    print(
        f"Regiões autónomas: {len(result.prices)} preços novos, {len(history)} no histórico "
        f"(Madeira até {result.state.madeira}, Açores até ao n.º {result.state.acores_number}"
        f"/{result.state.acores_year})"
    )
    if result.error is not None:
        raise result.error
    return 0


def verify_islands(directory: Path, today: date | None = None) -> int:
    check = islands.check_history(
        islands.read_history(directory / "precos.csv"), today or date.today()
    )
    latest = ", ".join(f"{islands.REGIONS[r]} em vigor desde {d}" for r, d in check.latest.items())
    print(f"Preços máximos em dia: {latest}")
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
    command = commands.add_parser("telegram", help="avisos de segunda-feira pelo Telegram")
    command.add_argument("--postos", type=Path, default=Path("data/stations_latest.parquet"))
    command.add_argument("--previsao", type=Path, default=Path("data/price_forecast.parquet"))
    command.add_argument(
        "--enviar", action="store_true", help="enviar (sem isto, só mostra as mensagens)"
    )
    command = commands.add_parser(
        "ilhas", help="preços máximos dos Açores e da Madeira (despachos novos, em PDF)"
    )
    command.add_argument("--pasta", type=Path, default=DEFAULT_ISLANDS)
    command.add_argument(
        "--desde",
        type=date.fromisoformat,
        default=date(2025, 1, 1),
        help="na primeira execução (sem estado.json), ler a partir deste dia",
    )
    command.add_argument("--hoje", type=date.fromisoformat, help=argparse.SUPPRESS)
    command = commands.add_parser(
        "verificar-ilhas",
        help="confirma que há o preço máximo da semana (Madeira) e do mês (Açores)",
    )
    command.add_argument("--pasta", type=Path, default=DEFAULT_ISLANDS)
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
    command.add_argument(
        "--evolucao",
        type=Path,
        default=Path("data/station_prices_daily.parquet"),
        help="as médias de cada fotografia, para o gráfico do resumo (sem o ficheiro, não escreve)",
    )
    command.add_argument(
        "--acompanhados",
        type=Path,
        default=Path("data/tracked_stations_daily.parquet"),
        help="o histórico dos postos acompanhados",
    )
    command.add_argument(
        "--concorrentes",
        type=Path,
        default=Path("data/tracked_station_competitors.parquet"),
        help="os concorrentes a 5 km dos postos acompanhados",
    )
    command.add_argument(
        "--ilhas",
        type=Path,
        default=Path("data/island_prices.parquet"),
        help="os preços máximos dos Açores e da Madeira (sem o ficheiro, não escreve)",
    )
    command.add_argument(
        "--boletim",
        type=Path,
        default=Path("data/road_fuel_prices.parquet"),
        help="o boletim europeu em € por litro, para as análises (sem o ficheiro, não escreve)",
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "dgeg":
            return snapshot(args.ficheiro, args.destino, args.data)
        if args.command == "mercados":
            return markets(args.ficheiros, args.destino)
        if args.command == "verificar-site":
            return verify_site(args.url, args.idade_maxima, args.hoje)
        if args.command == "telegram":
            return telegram(args.postos, args.previsao, args.enviar)
        if args.command == "site":
            extras = (args.evolucao, args.acompanhados, args.concorrentes)
            return site(
                args.postos,
                args.previsao,
                args.destino,
                args.paginas,
                args.armazem,
                extras,
                args.ilhas,
                args.boletim,
            )
        if args.command == "ilhas":
            return update_islands(args.pasta, args.desde, args.hoje)
        if args.command == "verificar-ilhas":
            return verify_islands(args.pasta, args.hoje)
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
        TelegramError,
        islands.IslandFormatError,
    ) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
