import io
import urllib.error
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from combustiveis import __main__ as cli
from combustiveis import ilhas
from combustiveis.ilhas import (
    IslandFormatError,
    IslandPrice,
    State,
    check_history,
    madeira_files,
    parse_acores,
    parse_madeira,
    pdf_text,
    read_history,
    read_state,
    update,
    write_history,
    write_state,
)


def make_pdf(lines: list[str]) -> bytes:
    """Um PDF de uma página com estas linhas (Helvetica, WinAnsi: tem o €, o ç e os acentos)."""

    def escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    ops = ["BT /F1 10 Tf 40 800 Td 12 TL", *[f"({escape(line)}) '" for line in lines], "ET"]
    stream = "\n".join(ops).encode("cp1252")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return out


# O texto dos despachos, como vem nos PDFs (resumido).
MADEIRA_2026 = [
    "Despacho Conjunto n.º 99/2026",
    "Homologação dos preços máximos de venda ao público dos combustíveis.",
    "Despacho Conjunto n.º 99/2026",
    "Sumário: Homologação dos preços máximos de venda ao público dos combustíveis.",
    "Texto: são homologados para vigorar na Região Autónoma da Madeira, a partir das 0 horas",
    "do dia 02 de novembro de 2026 os seguintes preços máximos de venda ao público:",
    "Gasolina super sem chumbo IO 95 .............................. 1,961 € por litro",
    "Gasóleo rodoviário ............................................ 2,125 € por litro",
    "Gasóleo colorido e marcado..................................... 1,677 € por litro",
]
# Em 2025, o € vinha antes do preço.
MADEIRA_2025 = [
    "despacho conjunto n.º 1/2025 sumário: homologação dos preços máximos de venda ao público",
    "dos combustíveis. a partir das 0 horas do dia 6 de janeiro de 2025 os seguintes preços:",
    "gasolina super sem chumbo io 95 ............... € 1,562 por litro",
    "gasóleo rodoviário.............................. € 1,321 por litro",
]
ACORES_2026 = [
    "ÍNDICE SEXTA-FEIRA, 30 DE OUTUBRO DE 2026 4107",
    "Despacho Normativo n.º 32/2026 de 30 de outubro de 2026",
    "Fixa os preços máximos de venda ao público do gasóleo colorido e marcado.",
    "Despacho Normativo n.º 33/2026 de 30 de outubro de 2026",
    "Fixa os preços máximos de venda ao público dos combustíveis líquidos.",
    "Despacho Normativo n.º 33/2026 de 30 de outubro de 2026",
    "1 - Fixar os seguintes preços máximos de venda ao público dos combustíveis líquidos:",
    "a) Gasolina sem chumbo I.O. 95 octanas, classificada pelos códigos da Nomenclatura",
    "Combinada (NC) 2710 12 45 - € 1,934 por litro, fornecida nos postos de abastecimento;",
    "b) Gasóleo, classificado pelo código NC 2710 19 41 a 2710 19 49 - € 1,994 por litro,",
    "2 - Fixar os seguintes preços máximos de venda ao público do gás de petróleo liquefeito:",
    "a) Butano em garrafas de 26 litros ou mais - € 2,199 por quilograma;",
    "3 - Os preços entram em vigor na Região Autónoma dos Açores a partir das zero horas do",
    "dia 1 de novembro de 2026.",
]
MADEIRA_URL = ilhas.MADEIRA_LISTING.format(year=2026)


def test_reads_the_text_of_a_pdf() -> None:
    assert pdf_text(make_pdf(["Gasóleo   rodoviário", "1,961 €"])) == "gasóleo rodoviário 1,961 €"


def test_parses_the_madeira_order() -> None:
    text = pdf_text(make_pdf(MADEIRA_2026))
    prices = parse_madeira(text, date(2026, 10, 30), "https://joram/x.pdf")
    assert [(p.fuel, p.price, p.valid_from) for p in prices] == [
        ("gasolina_95", Decimal("1.961"), date(2026, 11, 2)),
        ("gasoleo", Decimal("2.125"), date(2026, 11, 2)),
    ]
    assert prices[0].act == "Despacho Conjunto n.º 99/2026"
    old = parse_madeira(pdf_text(make_pdf(MADEIRA_2025)), date(2025, 1, 3), "u")
    assert [p.price for p in old] == [Decimal("1.562"), Decimal("1.321")]
    # Um PDF sem o despacho não tem preços.
    assert parse_madeira("outro despacho conjunto", date(2026, 10, 30), "u") == []


def test_parses_the_azores_order() -> None:
    text = pdf_text(make_pdf(ACORES_2026))
    prices = parse_acores(text, date(2026, 10, 30), "https://jo/I-2026-139-S0.pdf")
    assert [(p.fuel, p.price, p.valid_from, p.act) for p in prices] == [
        ("gasolina_95", Decimal("1.934"), date(2026, 11, 1), "Despacho Normativo n.º 33/2026"),
        ("gasoleo", Decimal("1.994"), date(2026, 11, 1), "Despacho Normativo n.º 33/2026"),
    ]
    assert parse_acores("um número sem combustíveis", date(2026, 10, 30), "u") == []


@pytest.mark.parametrize(
    ("lines", "message"),
    [
        ([line.replace("1,961", "9,961") for line in MADEIRA_2026], "Preço fora do esperado"),
        ([line.replace("Gasolina", "Gás") for line in MADEIRA_2026], "preço de Gasolina 95"),
        ([line for line in MADEIRA_2026 if "0 horas" not in line], "sem número ou sem data"),
        ([line.replace("novembro de 2026", "maio de 2027") for line in MADEIRA_2026], "datas"),
        ([line.replace("novembro", "brumário") for line in MADEIRA_2026], "Mês desconhecido"),
    ],
)
def test_a_madeira_order_that_cannot_be_read_fails(lines: list[str], message: str) -> None:
    with pytest.raises(IslandFormatError, match=message):
        parse_madeira(pdf_text(make_pdf(lines)), date(2026, 10, 30), "u")


@pytest.mark.parametrize(
    ("lines", "message"),
    [
        ([line.replace("1,994", "x") for line in ACORES_2026], "preço de Gasóleo"),
        ([line for line in ACORES_2026 if "zero horas" not in line], "sem número ou sem data"),
    ],
)
def test_an_azores_order_that_cannot_be_read_fails(lines: list[str], message: str) -> None:
    with pytest.raises(IslandFormatError, match=message):
        parse_acores(pdf_text(make_pdf(lines)), date(2026, 10, 30), "u")


LISTING = """<a href="IISerie-199-2026-11-03.pdf">x</a>
<a href="IISerie-197-2026-10-30Supl2.pdf">x</a><a href="IISerie-197-2026-10-30.pdf">x</a>
<a href="IISerie-196-2026-10-29.pdf">x</a><a href="IISerie-194-2026-10-27.pdf">x</a>
<a href="IISerie-190-2026-10-23Supl.pdf">x</a>"""


def test_madeira_files_after_a_day() -> None:
    assert madeira_files(LISTING, date(2026, 10, 23)) == [
        (date(2026, 10, 27), "IISerie-194-2026-10-27.pdf"),
        (date(2026, 10, 29), "IISerie-196-2026-10-29.pdf"),
        (date(2026, 10, 30), "IISerie-197-2026-10-30.pdf"),
        (date(2026, 10, 30), "IISerie-197-2026-10-30Supl2.pdf"),
        (date(2026, 11, 3), "IISerie-199-2026-11-03.pdf"),
    ]


def _site(files: dict[str, bytes]) -> Callable[[str], bytes]:
    def fetch(url: str) -> bytes:
        if url not in files:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO())  # type: ignore[arg-type]
        return files[url]

    return fetch


def _acores(year: int, number: int) -> str:
    return ilhas.ACORES_ISSUE.format(year=year, number=number, supplement=0)


def _files() -> dict[str, bytes]:
    other = make_pdf(["ÍNDICE QUINTA-FEIRA, 29 DE OUTUBRO DE 2026", "Outros atos"])
    return {
        MADEIRA_URL: LISTING.encode(),
        MADEIRA_URL + "IISerie-194-2026-10-27.pdf": make_pdf(["Outro despacho"]),
        MADEIRA_URL + "IISerie-196-2026-10-29.pdf": make_pdf(["Outro despacho"]),
        MADEIRA_URL + "IISerie-199-2026-11-03.pdf": make_pdf(["Outro despacho"]),
        MADEIRA_URL + "IISerie-197-2026-10-30.pdf": make_pdf(["Outro despacho"]),
        MADEIRA_URL + "IISerie-197-2026-10-30Supl2.pdf": make_pdf(MADEIRA_2026),
        _acores(2026, 138): other,
        _acores(2026, 139): make_pdf(ACORES_2026),
    }


def test_update_reads_only_what_is_new() -> None:
    state = State(date(2026, 10, 23), 2026, 137)
    logs: list[str] = []
    result = update(
        state, date(2026, 11, 4), fetch=_site(_files()), sleep=lambda _: None, log=logs.append
    )
    assert result.error is None
    assert result.state == State(date(2026, 11, 3), 2026, 139)
    assert {(p.region, p.fuel, p.price) for p in result.prices} == {
        ("madeira", "gasolina_95", Decimal("1.961")),
        ("madeira", "gasoleo", Decimal("2.125")),
        ("acores", "gasolina_95", Decimal("1.934")),
        ("acores", "gasoleo", Decimal("1.994")),
    }
    assert logs == [
        "Madeira: Despacho Conjunto n.º 99/2026, em vigor a 2026-11-02",
        "Açores: Despacho Normativo n.º 33/2026, em vigor a 2026-11-01",
    ]
    # Outra vez, sem nada de novo.
    again = update(result.state, date(2026, 11, 4), fetch=_site(_files()), sleep=lambda _: None)
    assert again.prices == []
    assert again.state == result.state


def test_update_moves_to_the_next_year() -> None:
    files = _files()
    files[_acores(2025, 160)] = make_pdf(["ÍNDICE TERÇA-FEIRA, 30 DE DEZEMBRO DE 2025"])
    state = State(date(2026, 10, 30), 2025, 159)
    result = update(state, date(2026, 11, 4), fetch=_site(files), sleep=lambda _: None)
    # 2026 começa no número 1, que não existe aqui: fica no 0 de 2026.
    assert result.state.acores_year == 2026
    assert result.state.acores_number == 0


def test_update_stops_at_an_order_it_cannot_read() -> None:
    files = _files()
    files[MADEIRA_URL + "IISerie-197-2026-10-30Supl2.pdf"] = make_pdf(MADEIRA_2026[:6])
    state = State(date(2026, 10, 23), 2026, 137)
    result = update(state, date(2026, 11, 4), fetch=_site(files), sleep=lambda _: None)
    assert isinstance(result.error, IslandFormatError)
    # Volta ao dia anterior, para ler o despacho outra vez depois de corrigida a leitura, e não
    # passa aos Açores.
    assert result.state == State(date(2026, 10, 29), 2026, 137)
    assert result.prices == []

    files = _files()
    files[_acores(2026, 139)] = make_pdf([line for line in ACORES_2026 if "zero" not in line])
    result = update(state, date(2026, 11, 4), fetch=_site(files), sleep=lambda _: None)
    assert isinstance(result.error, IslandFormatError)
    assert result.state.acores_number == 138


def test_update_raises_network_errors() -> None:
    def fetch(url: str) -> bytes:
        if "azores" in url:
            raise urllib.error.HTTPError(url, 500, "Erro", {}, io.BytesIO())  # type: ignore[arg-type]
        return _files()[url]

    with pytest.raises(urllib.error.HTTPError):
        update(State(date(2026, 10, 23), 2026, 137), date(2026, 11, 4), fetch, lambda _: None)


def _price(region: str, fuel: str, valid: date, price: str, published: date) -> IslandPrice:
    return IslandPrice(region, fuel, valid, Decimal(price), "Despacho", published, "u")


def test_history_keeps_one_price_per_day(tmp_path: Path) -> None:
    path = tmp_path / "ilhas" / "precos.csv"
    assert read_history(path) == []
    first = _price("madeira", "gasoleo", date(2026, 11, 2), "2.125", date(2026, 10, 30))
    # Um despacho que corrige outro: ganha o publicado depois.
    fixed = _price("madeira", "gasoleo", date(2026, 11, 2), "2.120", date(2026, 10, 31))
    older = _price("acores", "gasoleo", date(2026, 10, 1), "1.900", date(2026, 9, 28))
    rows = write_history(path, [fixed, first, older])
    assert rows == [older, fixed]
    assert read_history(path) == [older, fixed]
    assert path.read_text("utf-8").splitlines()[0] == ",".join(ilhas.COLUMNS)


def test_state_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "estado.json"
    assert read_state(path, date(2025, 1, 1)) == State(date(2024, 12, 31), 2025, 0)
    write_state(path, State(date(2026, 10, 30), 2026, 139))
    assert read_state(path, date(2025, 1, 1)) == State(date(2026, 10, 30), 2026, 139)


def test_check_history() -> None:
    prices = [
        _price("madeira", "gasoleo", date(2026, 11, 2), "2.125", date(2026, 10, 30)),
        _price("acores", "gasoleo", date(2026, 11, 1), "1.994", date(2026, 10, 30)),
    ]
    assert check_history(prices, date(2026, 11, 4)).latest == {
        "acores": date(2026, 11, 1),
        "madeira": date(2026, 11, 2),
    }
    # Nos primeiros dias do mês, ainda serve o do mês anterior nos Açores.
    october = [p for p in prices if p.region == "madeira"] + [
        _price("acores", "gasoleo", date(2026, 10, 1), "1.9", date(2026, 9, 28))
    ]
    check_history(october, date(2026, 11, 3))
    with pytest.raises(IslandFormatError, match="Açores: o último preço máximo é de 2026-10-01"):
        check_history(october, date(2026, 11, 4))
    with pytest.raises(IslandFormatError, match="Madeira: o último preço máximo é de 2026-11-02"):
        check_history(prices, date(2026, 11, 11))


def test_command_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(ilhas, "fetch_with_retries", _site(_files()))
    monkeypatch.setattr(ilhas, "PAUSE_SECONDS", 0)
    folder = tmp_path / "ilhas"
    args = ["ilhas", "--pasta", str(folder), "--desde", "2026-10-24", "--hoje", "2026-11-04"]
    folder.mkdir()
    write_state(folder / "estado.json", State(date(2026, 10, 23), 2026, 137))
    assert cli.main(args) == 0
    assert "4 preços novos, 4 no histórico" in capsys.readouterr().out
    assert cli.main(["verificar-ilhas", "--pasta", str(folder), "--hoje", "2026-11-04"]) == 0
    assert "Preços máximos em dia: Açores em vigor desde 2026-11-01" in capsys.readouterr().out
    assert cli.main(["verificar-ilhas", "--pasta", str(folder), "--hoje", "2026-12-04"]) == 1
    assert "Faltam preços" in capsys.readouterr().err

    files = _files()
    files[_acores(2026, 140)] = make_pdf([line for line in ACORES_2026 if "zero" not in line])
    monkeypatch.setattr(ilhas, "fetch_with_retries", _site(files))
    assert cli.main(args) == 1
    assert "sem número ou sem data" in capsys.readouterr().err
