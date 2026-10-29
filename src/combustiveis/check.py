"""Verificação do histórico de fotografias da DGEG (``data/landing/dgeg/AAAA-MM-DD.parquet``).

A DGEG só mostra o preço em vigor: um dia sem fotografia não se recupera. Por isso, o
agendamento confirma que a última fotografia é recente e que não perdeu postos de repente
(sinal de uma resposta incompleta ou de uma mudança no portal).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb

#: Quebra máxima de postos de uma fotografia para a anterior (20 %). De um dia para o outro
#: entram e saem poucos postos; uma quebra maior é quase sempre uma resposta incompleta.
MAX_DROP = 0.2


class SnapshotError(Exception):
    """O histórico de fotografias da DGEG parou ou tem uma fotografia suspeita."""


@dataclass(frozen=True)
class SnapshotCheck:
    latest: date
    stations: int
    previous: date | None
    previous_stations: int | None


def _snapshots(directory: Path) -> list[tuple[date, Path]]:
    found = []
    for path in directory.glob("*.parquet"):
        try:
            found.append((date.fromisoformat(path.stem), path))
        except ValueError:
            continue
    return sorted(found)


def _stations(path: Path) -> int:
    query = "SELECT count(DISTINCT station_id) FROM read_parquet(?)"
    rows = duckdb.execute(query, [str(path)]).fetchall()
    return int(rows[0][0])


def check_snapshots(
    directory: Path, max_age_days: int, today: date, max_drop: float = MAX_DROP
) -> SnapshotCheck:
    snapshots = _snapshots(directory)
    if not snapshots:
        raise SnapshotError(f"Não há fotografias da DGEG em {directory}")
    latest, path = snapshots[-1]
    age = (today - latest).days
    if age > max_age_days:
        raise SnapshotError(
            f"A última fotografia da DGEG é de {latest}, há {age} dias (o máximo é "
            f"{max_age_days}): a recolha diária (dgeg.yml) parou?"
        )
    stations = _stations(path)
    if len(snapshots) < 2:
        return SnapshotCheck(latest, stations, None, None)
    previous, previous_path = snapshots[-2]
    previous_stations = _stations(previous_path)
    if stations < previous_stations * (1 - max_drop):
        raise SnapshotError(
            f"A fotografia de {latest} tem {stations} postos, e a de {previous} tinha "
            f"{previous_stations}: a resposta do portal veio incompleta, ou o formato mudou?"
        )
    return SnapshotCheck(latest, stations, previous, previous_stations)
