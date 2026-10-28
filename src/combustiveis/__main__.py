"""``combustiveis ingest``: descarrega o histórico do Weekly Oil Bulletin e escreve a camada
landing (Parquet) em ``data/landing``.

``combustiveis ingest --ficheiro historico.xlsx`` usa um ficheiro já descarregado, e
``--idade-maxima 14`` falha se a última semana do boletim tiver mais de 14 dias (a execução
semanal usa-o para dar conta de uma fonte parada).

``combustiveis dgeg``: a fotografia de hoje dos preços de cada posto em Portugal (portal da
DGEG), em ``data/landing/dgeg/AAAA-MM-DD.parquet``.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from .dgeg import DgegFormatError, read_prices, search_url
from .landing import write_landing, write_station_snapshot
from .parse import FormatError, read_bulletin
from .source import PAGE_URL, SourceError, fetch, find_history_url

DEFAULT_LANDING = Path("data/landing")
DEFAULT_DGEG = DEFAULT_LANDING / "dgeg"


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
        data = fetch(url)
    prices = read_prices(data, day)
    target = write_station_snapshot(prices, directory)
    stations = len({p.station_id for p in prices})
    print(f"{len(prices)} preços de {stations} postos, do dia {day}, em {target}")
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
    args = parser.parse_args(argv)
    try:
        if args.command == "dgeg":
            return snapshot(args.ficheiro, args.destino, args.data)
        return ingest(args.ficheiro, args.destino, args.idade_maxima)
    except (SourceError, FormatError, DgegFormatError, StaleError, OSError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
