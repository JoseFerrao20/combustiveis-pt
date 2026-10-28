"""Gera tests/fixtures/dgeg_sample.json: uma amostra da resposta real do portal da DGEG
(PesquisarPostos), com o mesmo formato, só com alguns postos (de marcas e distritos
diferentes, mais os postos acompanhados do seed tracked_stations e os três mais próximos de
cada um) e todos os preços desses postos.

    uv run combustiveis dgeg --destino /tmp/x   # mostra o endereço do pedido
    curl -o resposta.json '<endereço>'
    uv run python scripts/make_dgeg_sample.py resposta.json

Fonte: Direção-Geral de Energia e Geologia, precoscombustiveis.dgeg.gov.pt (reutilização
livre, com indicação da fonte e da data de atualização dos preços).
"""

import csv
import json
import math
import sys
from pathlib import Path

BRANDS = ("GALP", "REPSOL", "BP", "PRIO", "INTERMARCHÉ", "Genérico", "CEPSA", "PINGO DOCE")
DISTRICTS = ("Lisboa", "Porto", "Bragança", "Faro")
ROOT = Path(__file__).parent.parent
TARGET = ROOT / "tests" / "fixtures" / "dgeg_sample.json"
TRACKED = ROOT / "transform" / "seeds" / "tracked_stations.csv"
NEIGHBOURS = 3


def distance_km(a: dict, b: dict) -> float:
    """Distância em linha reta (haversine), como no dbt (int_station_neighbours)."""
    lat1, lat2 = math.radians(a["Latitude"]), math.radians(b["Latitude"])
    dlat = lat2 - lat1
    dlong = math.radians(b["Longitude"] - a["Longitude"])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlong / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def tracked_and_neighbours(rows: list[dict]) -> list[int]:
    """Os postos acompanhados e os NEIGHBOURS mais próximos de cada um."""
    located = {row["Id"]: row for row in rows if row["Latitude"] and row["Longitude"]}
    with TRACKED.open(encoding="utf-8") as file:
        tracked = [int(line["station_id"]) for line in csv.DictReader(file)]
    stations: list[int] = []
    for station_id in tracked:
        here = located[station_id]
        others = sorted(
            (other for other in located.values() if other["Id"] != station_id),
            key=lambda other: distance_km(here, other),
        )
        stations += [station_id] + [other["Id"] for other in others[:NEIGHBOURS]]
    return stations


def main(source: str) -> None:
    body = json.loads(Path(source).read_text(encoding="utf-8"))
    rows = body["resultado"]
    stations: list[int] = []
    for brand in BRANDS:
        for district in DISTRICTS:
            for row in rows:
                if row["Marca"] == brand and row["Distrito"] == district:
                    if row["Id"] not in stations:
                        stations.append(row["Id"])
                    break
    for station_id in tracked_and_neighbours(rows):
        if station_id not in stations:
            stations.append(station_id)
    sample = [row for row in rows if row["Id"] in stations]
    for row in sample:
        row["Quantidade"] = len(sample)
    body["resultado"] = sample
    TARGET.write_text(json.dumps(body, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(sample)} preços de {len(stations)} postos em {TARGET}")


if __name__ == "__main__":
    main(sys.argv[1])
