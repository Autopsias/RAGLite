"""Sample chunks from Qdrant to examine fragmentation issues."""

import asyncio

from raglite.shared.clients import get_qdrant_client
from raglite.shared.config import settings


async def main():
    client = get_qdrant_client()

    # Get all chunks
    scroll_result = client.scroll(
        collection_name=settings.qdrant_collection_name,
        limit=100,
        with_payload=True,
        with_vectors=False,
    )

    chunks = scroll_result[0]

    print("=" * 80)
    print(f"CHUNK SAMPLING ANALYSIS (Total: {len(chunks)} chunks)")
    print("=" * 80)

    # Group by element type
    by_type = {}
    for chunk in chunks:
        elem_type = chunk.payload.get("element_type", "unknown")
        if elem_type not in by_type:
            by_type[elem_type] = []
        by_type[elem_type].append(chunk)

    print("\nCHUNKS BY ELEMENT TYPE:")
    for elem_type, chunk_list in sorted(by_type.items(), key=lambda x: -len(x[1])):
        print(f"  {elem_type}: {len(chunk_list)} chunks")

    # Sample table chunks to see if they're fragmented
    table_chunks = by_type.get("table", [])
    print(f"\n{'-' * 80}")
    print(f"SAMPLE TABLE CHUNKS (showing first 5 of {len(table_chunks)}):")
    print(f"{'-' * 80}")

    for i, chunk in enumerate(table_chunks[:5], 1):
        content = chunk.payload.get("text", "")
        section = chunk.payload.get("section_title", "None")
        page = chunk.payload.get("page_number", "?")
        word_count = chunk.payload.get("word_count", 0)

        print(f"\nTABLE CHUNK #{i}:")
        print(f"  Page: {page}, Section: {section}, Words: {word_count}")
        print("  Content preview (first 300 chars):")
        print(f"  {content[:300]}")
        if len(content) > 300:
            print(f"  ... ({len(content) - 300} more characters)")

    # Look for chunks with "Portugal Cement" variable costs
    print(f"\n{'-' * 80}")
    print("CHUNKS CONTAINING 'VARIABLE COST' (related to failed query #1):")
    print(f"{'-' * 80}")

    var_cost_chunks = [
        c
        for c in chunks
        if "variable" in c.payload.get("text", "").lower()
        and "cost" in c.payload.get("text", "").lower()
    ]
    print(f"Found {len(var_cost_chunks)} chunks with 'variable cost'")

    for i, chunk in enumerate(var_cost_chunks[:3], 1):
        content = chunk.payload.get("text", "")
        section = chunk.payload.get("section_title", "None")
        page = chunk.payload.get("page_number", "?")
        elem_type = chunk.payload.get("element_type", "unknown")

        print(f"\nVAR COST CHUNK #{i}:")
        print(f"  Page: {page}, Section: {section}, Type: {elem_type}")
        print("  Content preview (first 400 chars):")
        print(f"  {content[:400]}")

    # Look for EBITDA chunks (failed query category)
    print(f"\n{'-' * 80}")
    print("CHUNKS CONTAINING 'EBITDA' (related to failed queries #13-14, #20-21):")
    print(f"{'-' * 80}")

    ebitda_chunks = [c for c in chunks if "ebitda" in c.payload.get("text", "").lower()]
    print(f"Found {len(ebitda_chunks)} chunks with 'EBITDA'")

    for i, chunk in enumerate(ebitda_chunks[:3], 1):
        content = chunk.payload.get("text", "")
        section = chunk.payload.get("section_title", "None")
        page = chunk.payload.get("page_number", "?")
        elem_type = chunk.payload.get("element_type", "unknown")
        word_count = chunk.payload.get("word_count", 0)

        print(f"\nEBITDA CHUNK #{i}:")
        print(f"  Page: {page}, Section: {section}, Type: {elem_type}, Words: {word_count}")
        print("  Content preview (first 400 chars):")
        print(f"  {content[:400]}")

    # Check for chunks on pages mentioned in test errors (like page 46)
    print(f"\n{'-' * 80}")
    print("CHUNKS ON PAGE 46 (from test error example):")
    print(f"{'-' * 80}")

    page_46_chunks = [c for c in chunks if c.payload.get("page_number") == 46]
    print(f"Found {len(page_46_chunks)} chunks on page 46")

    for i, chunk in enumerate(page_46_chunks, 1):
        content = chunk.payload.get("text", "")
        section = chunk.payload.get("section_title", "None")
        elem_type = chunk.payload.get("element_type", "unknown")
        word_count = chunk.payload.get("word_count", 0)

        print(f"\nPAGE 46 CHUNK #{i}:")
        print(f"  Section: {section}, Type: {elem_type}, Words: {word_count}")
        print("  Content preview (first 300 chars):")
        print(f"  {content[:300]}")


asyncio.run(main())
