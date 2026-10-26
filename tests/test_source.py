import pytest

from combustiveis.source import SourceError, fetch, find_history_url

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
