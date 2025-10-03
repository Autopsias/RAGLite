#!/bin/bash
# Complete pipeline runner for QA fixes validation

set -e  # Exit on error

echo "========================================="
echo "FULL PIPELINE EXECUTION"
echo "========================================="

# Activate venv
source venv/bin/activate

echo -e "\n[1/5] Chunking documents..."
python spike/chunk_documents.py

echo -e "\n[2/5] Generating embeddings..."
python spike/generate_embeddings.py

echo -e "\n[3/5] Storing vectors in Qdrant..."
python spike/store_vectors.py

echo -e "\n[4/5] Testing MCP server (3 sample queries)..."
python spike/test_mcp_server.py

echo -e "\n[5/5] Running accuracy validation..."
python spike/create_ground_truth.py

echo -e "\n========================================="
echo "PIPELINE COMPLETE"
echo "========================================="

# Verify page numbers in final output
echo -e "\nVerifying page numbers in chunks..."
python3 -c "
import json
with open('spike_chunks.json') as f:
    data = json.load(f)
    chunks = data.get('chunks', [])
    with_pages = [c for c in chunks if c.get('metadata', {}).get('page_number') is not None]
    print(f'Total chunks: {len(chunks)}')
    print(f'Chunks with page numbers: {len(with_pages)}')
    print(f'Page number coverage: {len(with_pages)/len(chunks)*100:.1f}%')
    if with_pages:
        print(f'Sample chunk page: {with_pages[0][\"metadata\"][\"page_number\"]}')
"
