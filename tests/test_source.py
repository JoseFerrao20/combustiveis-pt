import io
import urllib.error
from collections.abc import Callable

import pytest

from combustiveis import source
from combustiveis.source import SourceError, fetch, fetch_with_retries, find_history_url

HISTORY = (
    "/document/download/906e60ca_en?filename=Weekly_Oil_Bulletin_Prices_History_maticni_4web.xlsx"
)
PAGE = f"""<a href="{HISTORY}">Download (4.28 MB - XLSX)</a>
<a href="/document/download/264c_en?filename=Weekly%20Oil%20Bulletin%20Weekly%20prices.xlsx">"""


def test_finds_the_history_link_in_the_page() -> None:
    assert find_history_url(PAGE) == "https://energy.ec.europa.eu" + HISTORY


def test_absolute_links_are_kept() -> None:
    page = '<a href="https://x.europa.eu/Weekly_Oil_Bulletin_Prices_History.xlsx">'
    assert find_history_url(page) == "https://x.europa.eu/Weekly_Oil_Bulletin_Prices_History.xlsx"


def test_page_without_the_link() -> None:
    with pytest.raises(SourceError, match="Não encontrei o link"):
        find_history_url("<html>mudaram a página</html>")


def test_only_https() -> None:
    with pytest.raises(SourceError, match="HTTPS"):
        fetch("file:///etc/passwd")


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x.pt", code, "erro", {}, io.BytesIO())  # type: ignore[arg-type]


def _fake_fetch(outcomes: list[bytes | OSError]) -> Callable[[str], bytes]:
    def fake(url: str) -> bytes:
        outcome = outcomes.pop(0)
        if isinstance(outcome, OSError):
            raise outcome
        return outcome

    return fake


def test_retries_after_a_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(source, "fetch", _fake_fetch([_http_error(500), TimeoutError(), b"ok"]))
    waits: list[float] = []
    assert fetch_with_retries("https://x.pt", delays=(1, 2, 3), sleep=waits.append) == b"ok"
    assert waits == [1, 2]


def test_gives_up_after_the_last_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(source, "fetch", _fake_fetch([_http_error(503)] * 3))
    waits: list[float] = []
    with pytest.raises(urllib.error.HTTPError):
        fetch_with_retries("https://x.pt", delays=(1, 2), sleep=waits.append)
    assert waits == [1, 2]


def test_client_errors_are_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(source, "fetch", _fake_fetch([_http_error(404)]))
    waits: list[float] = []
    with pytest.raises(urllib.error.HTTPError):
        fetch_with_retries("https://x.pt", delays=(1,), sleep=waits.append)
    assert waits == []
