"""Onde está o ficheiro do Weekly Oil Bulletin e como se descarrega."""

from __future__ import annotations

import html
import re
import urllib.request

PAGE_URL = "https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en"
BASE_URL = "https://energy.ec.europa.eu"
# O ficheiro do histórico tem sempre este nome, mas o endereço (com um identificador) muda
# quando a Comissão o substitui: por isso procura-se o link na página em cada execução.
HISTORY_FILENAME = "Weekly_Oil_Bulletin_Prices_History"
_LINK = re.compile(r'href="([^"]*' + HISTORY_FILENAME + r'[^"]*\.xlsx)"')
_TIMEOUT_SECONDS = 120


class SourceError(RuntimeError):
    """A página ou o ficheiro da Comissão não estão como esperado."""


def find_history_url(page: str) -> str:
    """O endereço do ficheiro do histórico, a partir do HTML da página do boletim."""
    match = _LINK.search(page)
    if match is None:
        raise SourceError(f"Não encontrei o link para {HISTORY_FILENAME}*.xlsx em {PAGE_URL}")
    url = html.unescape(match.group(1))
    return url if url.startswith("http") else BASE_URL + url


def fetch(url: str) -> bytes:
    if not url.startswith("https://"):
        raise SourceError(f"Só se descarrega por HTTPS: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "combustiveis-pt"})  # noqa: S310 (só https, verificado acima)
    with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:  # noqa: S310 (idem)
        data: bytes = response.read()
    return data
