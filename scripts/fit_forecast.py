"""Ajusta os coeficientes da previsão de segunda-feira (seed forecast_coefficients) e mede o
erro no período de teste (as semanas depois do ajuste).

Para cada produto, a mudança semanal do preço sem impostos em Portugal (boletim, euros por
1000 L) contra a mudança da cotação média em Nova Iorque na semana anterior e na outra antes
(int_market_weeks), por mínimos quadrados sem constante. Precisa do dbt já corrido com os dados
reais:

    uv run dbt build --project-dir transform --profiles-dir transform
    uv run python scripts/fit_forecast.py            # mostra os coeficientes e o erro
    uv run python scripts/fit_forecast.py --gravar   # e escreve-os no seed
"""

import argparse
import csv
from pathlib import Path

import duckdb

ROOT = Path(__file__).parent.parent
SEED = ROOT / "transform" / "seeds" / "forecast_coefficients.csv"
TRAIN_FROM, TRAIN_TO = "2012-01-02", "2023-12-25"
SERIES = {"euro95": "DGASNYH", "diesel": "DDFUELNYH"}
HEADER = [
    "product",
    "market_series",
    "beta_last_week",
    "beta_week_before",
    "trained_from",
    "trained_to",
]

QUERY = """
with prices as (
    select week, price_without_tax as p, vat_rate
    from fct_fuel_prices where country_code = 'PT' and product = $product
),
weeks as (select week, eur_per_1000l as m from int_market_weeks where product = $product)
select
    now.week,
    now.p - previous.p as y,
    w1.m - w2.m as x1,
    w2.m - w3.m as x2,
    now.vat_rate
from prices as now
join prices as previous on previous.week = now.week - interval 7 day
join weeks as w1 on w1.week = now.week - interval 7 day
join weeks as w2 on w2.week = now.week - interval 14 day
join weeks as w3 on w3.week = now.week - interval 21 day
order by now.week
"""


def fit(rows: list[tuple]) -> tuple[float, float]:
    """Mínimos quadrados sem constante, com duas variáveis (um sistema de duas equações)."""
    s11 = sum(r[2] * r[2] for r in rows)
    s22 = sum(r[3] * r[3] for r in rows)
    s12 = sum(r[2] * r[3] for r in rows)
    s1y = sum(r[2] * r[1] for r in rows)
    s2y = sum(r[3] * r[1] for r in rows)
    det = s11 * s22 - s12 * s12
    return (s22 * s1y - s12 * s2y) / det, (s11 * s2y - s12 * s1y) / det


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gravar", action="store_true", help="escrever os coeficientes no seed")
    parser.add_argument("--base", default=str(ROOT / "data" / "warehouse.duckdb"))
    args = parser.parse_args()
    db = duckdb.connect(args.base, read_only=True)
    lines = []
    for product, series in SERIES.items():
        rows = db.execute(QUERY, {"product": product}).fetchall()
        train = [r for r in rows if TRAIN_FROM <= str(r[0]) <= TRAIN_TO]
        test = [r for r in rows if str(r[0]) > TRAIN_TO]
        b1, b2 = fit(train)
        # Erro em cêntimos por litro, com o IVA de cada semana.
        cents = [(r[1] - (b1 * r[2] + b2 * r[3])) * (1 + r[4] / 100) / 10 for r in test]
        naive = [r[1] * (1 + r[4] / 100) / 10 for r in test]
        hits = sum((b1 * r[2] + b2 * r[3] > 0) == (r[1] > 0) for r in test if r[1] != 0)
        moved = sum(1 for r in test if r[1] != 0)
        print(
            f"{product}: beta {b1:.3f} e {b2:.3f} ({len(train)} semanas de ajuste). "
            f"Teste ({len(test)} semanas): erro médio {sum(map(abs, cents)) / len(cents):.2f} "
            f"cêntimos, contra {sum(map(abs, naive)) / len(naive):.2f} sem previsão; "
            f"acerta se sobe ou desce em {hits / moved:.0%}"
        )
        lines.append([product, series, f"{b1:.4f}", f"{b2:.4f}", TRAIN_FROM, TRAIN_TO])
    if args.gravar:
        with SEED.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file, lineterminator="\n")
            writer.writerow(HEADER)
            writer.writerows(lines)
        print(f"Escrito em {SEED.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
