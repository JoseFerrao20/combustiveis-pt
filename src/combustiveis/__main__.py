"""``combustiveis ingest``: descarrega o histórico do Weekly Oil Bulletin e escreve a camada
landing (Parquet) em ``data/landing``.

``combustiveis ingest --ficheiro historico.xlsx`` usa um ficheiro já descarregado.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .landing import write_landing
from .parse import FormatError, read_bulletin
from .source import PAGE_URL, SourceError, fetch, find_history_url

DEFAULT_LANDING = Path("data/landing")


def ingest(file: Path | None, landing: Path) -> int:
    if file is not None:
        data, url = file.read_bytes(), file.resolve().as_uri()
    else:
        url = find_history_url(fetch(PAGE_URL).decode("utf-8", errors="replace"))
        print(f"A descarregar {url}", file=sys.stderr)
        data = fetch(url)
    bulletin = read_bulletin(data)
    manifest = write_landing(bulletin, data, url, landing)
    print(
        f"{manifest.prices} preços e {manifest.taxes} impostos, até à semana de "
        f"{manifest.latest_week}, em {landing}/"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="combustiveis", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("ingest", help="descarrega o boletim e escreve o Parquet")
    command.add_argument("--ficheiro", type=Path, help="usar este .xlsx em vez de descarregar")
    command.add_argument("--destino", type=Path, default=DEFAULT_LANDING)
    args = parser.parse_args(argv)
    try:
        return ingest(args.ficheiro, args.destino)
    except (SourceError, FormatError, OSError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
