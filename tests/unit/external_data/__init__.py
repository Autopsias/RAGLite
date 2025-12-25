"""External data client unit tests - split from test_external_data_clients.py.

Story 7.1: Split test_external_data_clients.py (3,025 LOC -> <500 LOC per file)

This package organizes external data client tests into per-client modules
to improve AI comprehension and maintainability.

Modules:
    - test_ine_client.py: INE API client tests
    - test_basegov_client.py: BaseGov client tests
    - test_bpstat_client.py: BPstat client tests
    - test_omie_client.py: OMIE client tests
    - test_oil_bulletin_client.py: EU Oil Bulletin client tests
    - test_commodities_client.py: Commodities client tests
    - test_atic_client.py: ATIC cement client tests
    - test_ipma_client.py: IPMA weather client tests
    - test_exceptions.py: Shared exception tests
"""
