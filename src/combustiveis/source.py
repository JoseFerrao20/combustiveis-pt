"""Onde está o ficheiro do Weekly Oil Bulletin e como se descarrega."""

from __future__ import annotations

import html
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence

PAGE_URL = "https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en"
BASE_URL = "https://energy.ec.europa.eu"
# O ficheiro do histórico tem sempre este nome, mas o endereço (com um identificador) muda
# quando a Comissão o substitui: por isso procura-se o link na página em cada execução.
HISTORY_FILENAME = "Weekly_Oil_Bulletin_Prices_History"
_LINK = re.compile(r'href="([^"]*' + HISTORY_FILENAME + r'[^"]*\.xlsx)"')
_TIMEOUT_SECONDS = 120
# Identifica o projeto a quem recebe os pedidos (a Comissão e a DGEG).
USER_AGENT = "combustiveis-pt (+https://github.com/JoseFerrao20/combustiveis-pt)"


# Esperas entre tentativas quando o servidor falha (HTTP 5xx, tempo esgotado, ligação cortada).
# A fotografia da DGEG é semanal: perder uma por um erro passageiro é perder uma semana.
RETRY_DELAYS_SECONDS = (30, 120, 300)


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
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310 (só https, verificado acima)
    with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:  # noqa: S310 (idem)
        data: bytes = response.read()
    return data


def _is_transient(exc: OSError) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code >= 500
    return True  # URLError, TimeoutError, ConnectionError: a rede ou o servidor falharam.


def fetch_with_retries(
    url: str,
    delays: Sequence[float] = RETRY_DELAYS_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> bytes:
    """Como ``fetch``, mas tenta outra vez depois de cada espera se o erro for passageiro."""
    for delay in delays:
        try:
            return fetch(url)
        except OSError as exc:
            if not _is_transient(exc):
                raise
            print(f"aviso: {exc}; nova tentativa daqui a {delay:g} s", file=sys.stderr)
            sleep(delay)
    return fetch(url)
