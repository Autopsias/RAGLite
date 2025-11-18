#!/bin/bash

echo "=== Priority Classification Summary ==="
echo ""

P0_COUNT=$(grep -r '@pytest.mark.priority("P0")' tests --include='*.py' | wc -l | tr -d ' ')
P1_COUNT=$(grep -r '@pytest.mark.priority("P1")' tests --include='*.py' | wc -l | tr -d ' ')
P2_COUNT=$(grep -r '@pytest.mark.priority("P2")' tests --include='*.py' | wc -l | tr -d ' ')
TOTAL_PRIORITY=$((P0_COUNT + P1_COUNT + P2_COUNT))
TOTAL_TESTS=$(grep -r '@pytest.mark.test_id' tests --include='*.py' | wc -l | tr -d ' ')

echo "P0 (Critical): $P0_COUNT tests ($(echo "scale=1; $P0_COUNT * 100 / $TOTAL_TESTS" | bc)%)"
echo "P1 (High): $P1_COUNT tests ($(echo "scale=1; $P1_COUNT * 100 / $TOTAL_TESTS" | bc)%)"
echo "P2 (Medium): $P2_COUNT tests ($(echo "scale=1; $P2_COUNT * 100 / $TOTAL_TESTS" | bc)%)"
echo ""
echo "Total prioritized: $TOTAL_PRIORITY tests"
echo "Total tests: $TOTAL_TESTS tests"
echo "Remaining (P3): $((TOTAL_TESTS - TOTAL_PRIORITY)) tests"

echo ""
echo "=== P2 Test Files ==="
echo ""
echo "Unit tests with P2 markers:"
grep -l '@pytest.mark.priority("P2")' tests/unit/*.py 2>/dev/null | xargs basename -a | sort

echo ""
echo "Integration tests with P2 markers:"
grep -l '@pytest.mark.priority("P2")' tests/integration/*.py 2>/dev/null | xargs basename -a | sort
