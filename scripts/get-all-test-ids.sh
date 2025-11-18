#!/bin/bash

# Get all test IDs that need P2 marking
echo "=== Getting actual test IDs for P2 marking ==="

echo -e "\n=== Integration tests ==="

echo -e "\ntest_pypdfium_ingestion.py:"
grep -o '@pytest.mark.test_id("[^"]*")' tests/integration/test_pypdfium_ingestion.py | sed 's/@pytest.mark.test_id("\(.*\)")/\1/'

echo -e "\ntest_page_parallelism.py:"
grep -o '@pytest.mark.test_id("[^"]*")' tests/integration/test_page_parallelism.py | sed 's/@pytest.mark.test_id("\(.*\)")/\1/'

echo -e "\ntest_metadata_injection.py:"
grep -o '@pytest.mark.test_id("[^"]*")' tests/integration/test_metadata_injection.py | sed 's/@pytest.mark.test_id("\(.*\)")/\1/'

echo -e "\ntest_e2e_query_validation.py:"
grep -o '@pytest.mark.test_id("[^"]*")' tests/integration/test_e2e_query_validation.py | sed 's/@pytest.mark.test_id("\(.*\)")/\1/'

echo -e "\ntest_story_2_14_excerpt_validation.py:"
grep -o '@pytest.mark.test_id("[^"]*")' tests/integration/test_story_2_14_excerpt_validation.py | sed 's/@pytest.mark.test_id("\(.*\)")/\1/'

echo -e "\ntest_table_retrieval.py:"
grep -o '@pytest.mark.test_id("[^"]*")' tests/integration/test_table_retrieval.py | sed 's/@pytest.mark.test_id("\(.*\)")/\1/'

echo -e "\ntest_sql_routing.py:"
grep -o '@pytest.mark.test_id("[^"]*")' tests/integration/test_sql_routing.py | sed 's/@pytest.mark.test_id("\(.*\)")/\1/'

echo -e "\ntest_retrieval_integration.py:"
grep -o '@pytest.mark.test_id("[^"]*")' tests/integration/test_retrieval_integration.py | sed 's/@pytest.mark.test_id("\(.*\)")/\1/'

echo -e "\ntest_mcp_server.py:"
grep -o '@pytest.mark.test_id("[^"]*")' tests/integration/test_mcp_server.py | sed 's/@pytest.mark.test_id("\(.*\)")/\1/'

echo -e "\ntest_ingestion_integration.py:"
grep -o '@pytest.mark.test_id("[^"]*")' tests/integration/test_ingestion_integration.py | sed 's/@pytest.mark.test_id("\(.*\)")/\1/'

echo -e "\ntest_main_integration.py:"
grep -o '@pytest.mark.test_id("[^"]*")' tests/integration/test_main_integration.py | sed 's/@pytest.mark.test_id("\(.*\)")/\1/'
