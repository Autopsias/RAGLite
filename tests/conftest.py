# tests/conftest.py
"""Root conftest.py for pytest configuration and custom options."""


def pytest_addoption(parser):
    """Register custom pytest command-line options."""
    parser.addoption(
        "--skip-ingestion",
        action="store_true",
        default=False,
        help="Skip data ingestion (use pre-existing Qdrant collection data from init-ci-qdrant.py)",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "skip_ingestion: skip ingestion tests when --skip-ingestion flag is used",
    )
