"""Shared fixtures and data for external data integration tests."""

from unittest.mock import MagicMock

import pytest

# =============================================================================
# Sample Data for Integration Tests
# =============================================================================

SAMPLE_INE_RESPONSE = {
    "Dados": {
        "202401": [
            {"valor": 1234, "geocod": "Lisboa", "variacao_homologa": 5.2},
            {"valor": 987, "geocod": "Porto", "variacao_homologa": 3.1},
        ],
        "202402": [
            {"valor": 1456, "geocod": "Lisboa", "variacao_homologa": 4.8},
        ],
        "202403": [
            {"valor": 1523, "geocod": "Lisboa", "variacao_homologa": 6.1},
        ],
    }
}

# Story 6.9.3: Updated response format for new BPstat API
SAMPLE_BPSTAT_RESPONSE = {
    "observations": [
        {"period": "2024-01", "value": 3.45, "series_id": "12710733"},
        {"period": "2024-02", "value": 3.52, "series_id": "12710733"},
        {"period": "2024-03", "value": 3.48, "series_id": "12710733"},
    ]
}

# Story 6.9.2: Updated OMIE response format
SAMPLE_OMIE_RESPONSE = """MARGINALPDBC;2024;1;1;1;45,50;46,00
MARGINALPDBC;2024;1;1;2;44,20;45,00
MARGINALPDBC;2024;1;1;3;43,80;44,50
MARGINALPDBC;2024;1;1;4;42,10;43,00
MARGINALPDBC;2024;1;1;5;41,50;42,50
MARGINALPDBC;2024;1;1;6;43,00;44,00
MARGINALPDBC;2024;1;1;7;48,20;49,00
MARGINALPDBC;2024;1;1;8;55,30;56,00
MARGINALPDBC;2024;1;1;9;58,40;59,00
MARGINALPDBC;2024;1;1;10;57,80;58,50
MARGINALPDBC;2024;1;1;11;56,20;57,00
MARGINALPDBC;2024;1;1;12;54,80;55,50
MARGINALPDBC;2024;1;1;13;53,20;54,00
MARGINALPDBC;2024;1;1;14;52,10;53,00
MARGINALPDBC;2024;1;1;15;51,80;52,50
MARGINALPDBC;2024;1;1;16;53,40;54,00
MARGINALPDBC;2024;1;1;17;56,80;57,50
MARGINALPDBC;2024;1;1;18;62,30;63,00
MARGINALPDBC;2024;1;1;19;68,40;69,00
MARGINALPDBC;2024;1;1;20;65,20;66,00
MARGINALPDBC;2024;1;1;21;58,90;59,50
MARGINALPDBC;2024;1;1;22;52,10;53,00
MARGINALPDBC;2024;1;1;23;47,30;48,00
MARGINALPDBC;2024;1;1;24;44,80;45,50"""

SAMPLE_BASEGOV_RESPONSE = {
    "items": [
        {
            "id": "CT-2024-001",
            "dataPublicacao": "2024-01-15",
            "precoContratual": 2500000,
            "objectoContrato": "Construction of new highway section A-42",
            "entidadeAdjudicante": "Infraestruturas de Portugal",
            "adjudicatario": "Construções ABC, S.A.",
            "cpv": "45233000",
            "localizacao": "Distrito de Lisboa",
        },
        {
            "id": "CT-2024-002",
            "dataPublicacao": "2024-02-20",
            "precoContratual": 850000,
            "objectoContrato": "Building renovation municipal center",
            "entidadeAdjudicante": "Câmara Municipal de Porto",
            "adjudicatario": "Renovações XYZ, Lda",
            "cpv": "45210000",
            "localizacao": "Porto",
        },
    ]
}

SAMPLE_IPMA_RESPONSE = {
    "tMed": 15.5,
    "tMax": 20.0,
    "tMin": 10.5,
    "prec": 2.5,
    "humidade": 72.0,
    "vento": 18.5,
}

# Story 6.9.4: EU Oil Bulletin now uses XLSX format
SAMPLE_EU_OIL_BULLETIN_PRICES = [
    {"date": "2024-01-08", "country": "Portugal", "price": 1.456},
    {"date": "2024-01-15", "country": "Portugal", "price": 1.478},
    {"date": "2024-01-22", "country": "Portugal", "price": 1.492},
    {"date": "2024-02-05", "country": "Portugal", "price": 1.501},
    {"date": "2024-02-12", "country": "Portugal", "price": 1.485},
    {"date": "2024-03-04", "country": "Portugal", "price": 1.468},
    {"date": "2024-03-11", "country": "Portugal", "price": 1.452},
]


@pytest.fixture
def sample_ine_response():
    """Return sample INE API response."""
    return SAMPLE_INE_RESPONSE


@pytest.fixture
def sample_bpstat_response():
    """Return sample BPstat API response."""
    return SAMPLE_BPSTAT_RESPONSE


@pytest.fixture
def sample_omie_response():
    """Return sample OMIE API response."""
    return SAMPLE_OMIE_RESPONSE


@pytest.fixture
def sample_basegov_response():
    """Return sample BaseGov API response."""
    return SAMPLE_BASEGOV_RESPONSE


@pytest.fixture
def sample_ipma_response():
    """Return sample IPMA API response."""
    return SAMPLE_IPMA_RESPONSE


@pytest.fixture
def sample_eu_oil_bulletin_prices():
    """Return sample EU Oil Bulletin prices."""
    return SAMPLE_EU_OIL_BULLETIN_PRICES


@pytest.fixture
def mock_response():
    """Create a reusable mock HTTP response."""

    def _make_mock(content=None, json_data=None, text_data=None):
        response = MagicMock()
        if json_data:
            response.json.return_value = json_data
        if text_data:
            response.text = text_data
        response.raise_for_status = MagicMock()
        return response

    return _make_mock
