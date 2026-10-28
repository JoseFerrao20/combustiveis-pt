"""Gera tests/fixtures/dgeg_sample.json: uma amostra da resposta real do portal da DGEG
(PesquisarPostos), com o mesmo formato, só com alguns postos (de marcas e distritos
diferentes) e todos os preços desses postos.

    uv run combustiveis dgeg --destino /tmp/x   # mostra o endereço do pedido
    curl -o resposta.json '<endereço>'
    uv run python scripts/make_dgeg_sample.py resposta.json

Fonte: Direção-Geral de Energia e Geologia, precoscombustiveis.dgeg.gov.pt (reutilização
livre, com indicação da fonte e da data de atualização dos preços).
"""

import json
import sys
from pathlib import Path

BRANDS = ("GALP", "REPSOL", "BP", "PRIO", "INTERMARCHÉ", "Genérico", "CEPSA", "PINGO DOCE")
DISTRICTS = ("Lisboa", "Porto", "Bragança", "Faro")
TARGET = Path(__file__).parent.parent / "tests" / "fixtures" / "dgeg_sample.json"


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
    sample = [row for row in rows if row["Id"] in stations]
    for row in sample:
        row["Quantidade"] = len(sample)
    body["resultado"] = sample
    TARGET.write_text(json.dumps(body, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(sample)} preços de {len(stations)} postos em {TARGET}")


if __name__ == "__main__":
    main(sys.argv[1])
