from pathlib import Path

import pytest

SAMPLE = Path(__file__).parent / "fixtures" / "oil_bulletin_sample.xlsx"


@pytest.fixture(scope="session")
def sample_bytes() -> bytes:
    return SAMPLE.read_bytes()
