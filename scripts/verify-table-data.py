#!/usr/bin/env python3
"""Verify table cell data was extracted by searching for known values."""

from qdrant_client import QdrantClient

# Connect to Qdrant
client = QdrantClient(url="http://localhost:6333")

# Get all points
collection_name = "financial_docs"
points = client.scroll(
    collection_name=collection_name, limit=500, with_payload=True, with_vectors=False
)[0]

print(f"\nSearching {len(points)} chunks for table cell data...")
print("=" * 80)

# Search for known table values from page 46
test_values = ["23.2", "50.6%", "20.3", "29.4", "104,647", "EUR/ton"]

results = {}
for value in test_values:
    results[value] = []

for point in points:
    text = point.payload.get("text", "")
    page = point.payload.get("page_number", "?")

    for value in test_values:
        if value in text:
            results[value].append(
                {
                    "page": page,
                    "chunk_id": point.payload.get("chunk_id", "?"),
                    "preview": text[:150],
                }
            )

print("\nRESULTS:")
print("-" * 80)
for value, matches in results.items():
    if matches:
        print(f"\n✅ Found '{value}' in {len(matches)} chunk(s):")
        for match in matches[:2]:  # Show first 2 matches
            print(f"   Page {match['page']}: {match['preview']}...")
    else:
        print(f"\n❌ NOT FOUND: '{value}'")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)

# Summary
found_count = sum(1 for matches in results.values() if matches)
total_count = len(test_values)
print(f"\nTable data extraction: {found_count}/{total_count} values found")

if found_count >= 3:
    print("✅ SUCCESS: Table cell data is being extracted!")
else:
    print("❌ FAILURE: Table cell data NOT found in chunks")
