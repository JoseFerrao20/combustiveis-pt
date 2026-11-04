"""Os preços máximos dos combustíveis nos Açores e na Madeira (ADR 0007).

A DGEG só tem os postos do continente. Nas regiões autónomas, o governo regional fixa um preço
máximo de venda ao público, publicado em PDF no jornal oficial:

- **Madeira:** todas as semanas, num despacho conjunto do JORAM (II série, quase sempre num
  suplemento de sexta-feira), em vigor a partir de segunda. A lista dos PDFs de cada ano está
  numa página do JORAM.
- **Açores:** todos os meses, num despacho normativo do Jornal Oficial (I série), em vigor no
  dia 1. O site do Jornal Oficial tem uma verificação anti-robôs em todas as páginas, menos
  nos PDFs: os números da I série têm endereços sequenciais (``I-2026-139-S0.pdf``), com o
  índice e os atos completos, e seguem-se um a um.

Os PDFs não têm um formato combinado: a leitura procura frases que se repetem há anos e falha
com ``IslandFormatError`` quando encontra o despacho mas não consegue ler os preços ou a data
(em vez de guardar um valor errado). O histórico fica no ramo ``dados`` (``ilhas/precos.csv``),
com o que já se leu em ``ilhas/estado.json``, para cada execução só ler o que saiu de novo.
"""

from __future__ import annotations

import csv
import html
import json
import re
import time
import urllib.error
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pypdfium2

from .source import fetch_with_retries

MADEIRA_LISTING = "https://joram.madeira.gov.pt/joram/2serie/Ano%20de%20{year}/"
ACORES_ISSUE = "https://jo.azores.gov.pt/pdf/jornais/I-{year}-{number:03d}-S{supplement}.pdf"

REGIONS = {"acores": "Açores", "madeira": "Madeira"}
FUELS = {"gasolina_95": "Gasolina 95", "gasoleo": "Gasóleo"}
COLUMNS = ("region", "fuel", "valid_from", "price", "act", "published", "source_url")

#: Os preços máximos fora disto são quase de certeza uma leitura errada.
PRICE_RANGE = (Decimal("0.8"), Decimal("3.5"))
#: Os despachos entram em vigor poucos dias depois de publicados (o dos Açores, no dia 1).
MAX_DAYS_TO_VALID = 40

#: As páginas do sumário de um número do JORAM.
SUMMARY_PAGES = 2
#: Uma pausa entre pedidos, para não sobrecarregar os servidores das regiões.
PAUSE_SECONDS = 1.0

_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
_DATE = r"(\d{1,2})\s+de\s+([a-zçáéíóú]+)\s+de\s+(\d{4})"
_PRICE = r"(\d,\d{3})"

_MADEIRA_ACT = re.compile(r"homologação dos preços máximos de venda ao público dos combustíveis")
_MADEIRA_NUMBER = re.compile(r"despacho conjunto n\.º\s*(\d+/\d{4})")
_MADEIRA_FROM = re.compile(r"a partir das 0 horas do dia " + _DATE)
_MADEIRA_PRICES = {
    # O € vem antes ou depois do preço, conforme o ano ("€ 1,562" ou "1,961 €").
    "gasolina_95": re.compile(r"gasolina[^€\d]{0,40}?95[ .…]*(?:€\s*)?" + _PRICE + r"\s*(?:€|por)"),
    "gasoleo": re.compile(r"gasóleo rodoviário[ .…]*(?:€\s*)?" + _PRICE + r"\s*(?:€|por)"),
}
_MADEIRA_FILE = re.compile(r'href="(IISerie-\d+-(\d{4}-\d{2}-\d{2})(?:Supl\d*)?\.pdf)"')

_ACORES_ACT = re.compile(
    r"fixar os seguintes preços máximos de venda ao público dos combustíveis líquidos"
)
_ACORES_NUMBER = re.compile(r"despacho normativo n\.º\s*([\d-]+[a-z]?/\d{4})")
_ACORES_FROM = re.compile(r"a partir das zero horas do dia " + _DATE)
_ACORES_PRICES = {
    "gasolina_95": re.compile(
        r"gasolina sem chumbo i\.o\. 95.{0,150}?€\s*" + _PRICE + " por litro"
    ),
    "gasoleo": re.compile(r"\bb\)\s*gasóleo,.{0,150}?€\s*" + _PRICE + " por litro"),
}


class IslandFormatError(ValueError):
    """Um despacho dos preços máximos que não se consegue ler como esperado."""


@dataclass(frozen=True)
class IslandPrice:
    region: str
    fuel: str
    valid_from: date
    price: Decimal
    act: str
    published: date
    source_url: str


@dataclass
class State:
    """O que já se leu: a data do último ficheiro da Madeira e o último número dos Açores."""

    madeira: date
    acores_year: int
    acores_number: int


def pdf_text(data: bytes, pages: int | None = None) -> str:
    """O texto de um PDF (das primeiras ``pages`` páginas, ou de todas), numa linha só e em
    minúsculas (os PDFs partem as frases a meio)."""
    document = pypdfium2.PdfDocument(data)
    try:
        count = len(document) if pages is None else min(pages, len(document))
        texts = [document[i].get_textpage().get_text_bounded() for i in range(count)]
    finally:
        document.close()
    return re.sub(r"\s+", " ", " ".join(texts)).lower()


def _date(day: str, month: str, year: str) -> date:
    if month not in _MONTHS:
        raise IslandFormatError(f"Mês desconhecido: {month!r}")
    return date(int(year), _MONTHS[month], int(day))


def _price(value: str) -> Decimal:
    price = Decimal(value.replace(",", "."))
    if not PRICE_RANGE[0] <= price <= PRICE_RANGE[1]:
        raise IslandFormatError(f"Preço fora do esperado: {value} €")
    return price


def _check_dates(valid_from: date, published: date, url: str) -> None:
    if not 0 <= (valid_from - published).days <= MAX_DAYS_TO_VALID:
        raise IslandFormatError(
            f"{url}: em vigor a {valid_from}, publicado a {published}: as datas não batem certo"
        )


def parse_madeira(text: str, published: date, url: str) -> list[IslandPrice]:
    """Os preços de um PDF do JORAM, ou nada se não tiver o despacho dos preços máximos."""
    start = _MADEIRA_ACT.search(text)
    if start is None:
        return []
    # O sumário da primeira página também tem a frase: o texto do despacho vem depois.
    body = text[start.start() :]
    valid = _MADEIRA_FROM.search(body)
    # O número é o do despacho logo antes da frase (o número pode ter outros despachos).
    numbers = list(_MADEIRA_NUMBER.finditer(text, 0, start.start()))
    number = numbers[-1] if numbers else None
    if valid is None or number is None:
        raise IslandFormatError(f"{url}: despacho dos preços máximos sem número ou sem data")
    valid_from = _date(*valid.groups())
    _check_dates(valid_from, published, url)
    prices = []
    for fuel, pattern in _MADEIRA_PRICES.items():
        match = pattern.search(body, valid.end())
        if match is None:
            raise IslandFormatError(f"{url}: não encontrei o preço de {FUELS[fuel]}")
        act = f"Despacho Conjunto n.º {number.group(1)}"
        prices.append(
            IslandPrice("madeira", fuel, valid_from, _price(match.group(1)), act, published, url)
        )
    return prices


def parse_acores(text: str, published: date, url: str) -> list[IslandPrice]:
    """Os preços de um número do Jornal Oficial dos Açores, ou nada se não tiver o despacho.

    Um número tem vários atos (o do gasóleo agrícola também fixa "preços máximos"): procura-se
    a frase dos combustíveis líquidos, o número do despacho antes dela e a data depois.
    """
    found = []
    for start in _ACORES_ACT.finditer(text):
        numbers = list(_ACORES_NUMBER.finditer(text, 0, start.start()))
        valid = _ACORES_FROM.search(text, start.end())
        if not numbers or valid is None:
            raise IslandFormatError(f"{url}: despacho dos preços máximos sem número ou sem data")
        valid_from = _date(*valid.groups())
        _check_dates(valid_from, published, url)
        section = text[start.end() : valid.start()]
        act = f"Despacho Normativo n.º {numbers[-1].group(1)}"
        for fuel, pattern in _ACORES_PRICES.items():
            match = pattern.search(section)
            if match is None:
                raise IslandFormatError(f"{url}: não encontrei o preço de {FUELS[fuel]}")
            found.append(
                IslandPrice("acores", fuel, valid_from, _price(match.group(1)), act, published, url)
            )
    return found


def madeira_files(listing: str, after: date) -> list[tuple[date, str]]:
    """Os PDFs da página de um ano do JORAM publicados depois de ``after``, do mais antigo para o
    mais recente. O despacho sai quase sempre à sexta-feira, mas numa semana com feriados sai
    antes (o de 29/12/2025 saiu a 23/12): leem-se todos os dias, primeiro só o sumário."""
    files = set()
    for name, day in _MADEIRA_FILE.findall(listing):
        published = date.fromisoformat(day)
        if published > after:
            files.add((published, html.unescape(name)))
    return sorted(files)


def _acores_published(text: str, url: str) -> date:
    match = re.search(r"feira, " + _DATE, text[:300]) or re.search(_DATE, text[:300])
    if match is None:
        raise IslandFormatError(f"{url}: não encontrei a data do número")
    return _date(*match.groups())


def _is_missing(exc: Exception) -> bool:
    return isinstance(exc, urllib.error.HTTPError) and exc.code == 404


@dataclass(frozen=True)
class Update:
    prices: list[IslandPrice]
    state: State
    #: O erro que fez parar a leitura (o estado fica no último ficheiro lido sem problemas).
    error: IslandFormatError | None = None


def update(
    state: State,
    today: date,
    fetch: Callable[[str], bytes] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    log: Callable[[str], None] = print,
) -> Update:
    """Lê o que saiu desde a última execução e devolve os preços novos e o estado seguinte.

    Um despacho que não se consegue ler faz parar a leitura dessa região: o estado fica antes
    dele, para se voltar a ler depois de corrigida a leitura.
    """
    get = fetch or fetch_with_retries
    prices: list[IslandPrice] = []
    error: IslandFormatError | None = None

    # Madeira: a página de cada ano tem a lista dos PDFs.
    madeira = state.madeira
    try:
        for year in range(state.madeira.year, today.year + 1):
            listing = get(MADEIRA_LISTING.format(year=year)).decode("utf-8", "replace")
            for published, name in madeira_files(listing, state.madeira):
                url = MADEIRA_LISTING.format(year=year) + name
                sleep(PAUSE_SECONDS)
                data = get(url)
                madeira = max(madeira, published)
                # Alguns números têm centenas de páginas: o sumário (no início) diz se o
                # despacho dos preços está lá, e só então se lê o resto.
                summary = pdf_text(data, pages=SUMMARY_PAGES)
                if _MADEIRA_ACT.search(summary) is None:
                    continue
                found = parse_madeira(pdf_text(data), published, url)
                if found:
                    log(f"Madeira: {found[0].act}, em vigor a {found[0].valid_from}")
                prices += found
    except IslandFormatError as exc:
        error = exc
        # Volta ao dia anterior ao do ficheiro com o problema, para o ler outra vez.
        madeira = min(madeira, published - timedelta(days=1))
        prices = [p for p in prices if p.published <= madeira]

    # Açores: os números seguem-se; o fim do ano (ou o último número saído) é um 404.
    year, number = state.acores_year, state.acores_number
    while error is None and year <= today.year:
        url = ACORES_ISSUE.format(year=year, number=number + 1, supplement=0)
        sleep(PAUSE_SECONDS)
        try:
            data = get(url)
        except OSError as exc:
            if not _is_missing(exc):
                raise
            if year == today.year:
                break
            year, number = year + 1, 0
            continue
        text = pdf_text(data)
        try:
            found = parse_acores(text, _acores_published(text, url), url)
        except IslandFormatError as exc:
            error = exc
            break
        number += 1
        if found:
            log(f"Açores: {found[0].act}, em vigor a {found[0].valid_from}")
        prices += found

    return Update(prices, State(madeira, year, number), error)


def read_history(path: Path) -> list[IslandPrice]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as file:
        return [
            IslandPrice(
                row["region"],
                row["fuel"],
                date.fromisoformat(row["valid_from"]),
                Decimal(row["price"]),
                row["act"],
                date.fromisoformat(row["published"]),
                row["source_url"],
            )
            for row in csv.DictReader(file)
        ]


def write_history(path: Path, prices: Iterable[IslandPrice]) -> list[IslandPrice]:
    """Junta e escreve o histórico: um preço por região, combustível e data (o mais recente
    publicado ganha, se um despacho corrigir outro)."""
    unique: dict[tuple[str, str, date], IslandPrice] = {}
    for price in sorted(prices, key=lambda p: p.published):
        unique[(price.region, price.fuel, price.valid_from)] = price
    rows = sorted(unique.values(), key=lambda p: (p.region, p.fuel, p.valid_from))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: str(v) for k, v in asdict(row).items()})
    return rows


def read_state(path: Path, start: date) -> State:
    if not path.exists():
        return State(start - timedelta(days=1), start.year, 0)
    data = json.loads(path.read_text("utf-8"))
    return State(
        date.fromisoformat(data["madeira"]), int(data["acores_year"]), int(data["acores_number"])
    )


def write_state(path: Path, state: State) -> None:
    data = {
        "madeira": state.madeira.isoformat(),
        "acores_year": state.acores_year,
        "acores_number": state.acores_number,
    }
    path.write_text(json.dumps(data, indent=2) + "\n", "utf-8")


@dataclass(frozen=True)
class IslandCheck:
    latest: dict[str, date]


def check_history(prices: list[IslandPrice], today: date) -> IslandCheck:
    """Falha se faltar o preço em vigor: o da semana na Madeira (em vigor há no máximo 8 dias)
    e o do mês nos Açores (em vigor desde o dia 1, com 3 dias de folga no início do mês)."""
    latest = {
        region: max((p.valid_from for p in prices if p.region == region), default=date.min)
        for region in REGIONS
    }
    problems = []
    if (today - latest["madeira"]).days > 8:
        problems.append(f"Madeira: o último preço máximo é de {latest['madeira']}")
    month_start = today.replace(day=1)
    expected = month_start if today.day > 3 else (month_start - timedelta(days=1)).replace(day=1)
    if latest["acores"] < expected:
        problems.append(f"Açores: o último preço máximo é de {latest['acores']}")
    if problems:
        raise IslandFormatError(
            "Faltam preços das regiões autónomas (o despacho mudou de formato ou não saiu?):\n- "
            + "\n- ".join(problems)
        )
    return IslandCheck(latest)
