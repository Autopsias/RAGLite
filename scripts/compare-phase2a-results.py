"""Compare Phase 2A results before/after query preprocessing."""


# Load previous results (if saved)
# For now, let's look at the full test output to understand failures

print("Analyzing accuracy regression: 52% → 46% (-6pp)")
print()
print("This suggests query preprocessing is breaking some queries.")
print()
print("Possible causes:")
print("1. Stopword removal is too aggressive - removing meaningful business terms")
print("2. Temporal extraction is incorrectly matching non-temporal terms")
print("3. Keyword simplification is losing important context")
print()
print("Need to inspect actual failures to understand root cause.")
