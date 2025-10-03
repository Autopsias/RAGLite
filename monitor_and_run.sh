#!/bin/bash
# Monitor ingestion and auto-run pipeline when complete

echo "Monitoring ingestion (checking every 30s)..."
echo "Started at: 23:32:35, ETA: 23:39-23:40"

for i in {1..15}; do
    sleep 30
    
    if [ -f "spike_ingestion_result.json" ]; then
        echo "✅ Ingestion complete! File detected."
        
        # Verify page extraction worked
        echo -e "\n🔍 Verifying page extraction..."
        python3 -c "
import json
with open('spike_ingestion_result.json') as f:
    data = json.load(f)
    pages = data.get('pages', [])
    non_empty = [p for p in pages if p.get('char_count', 0) > 0]
    print(f'Total pages: {len(pages)}')
    print(f'Pages with content: {len(non_empty)}')
    print(f'Coverage: {len(non_empty)/len(pages)*100:.1f}%' if pages else 'N/A')
    
    if non_empty:
        sample = non_empty[0]
        print(f'\\nSample page {sample[\"page_number\"]}: {sample[\"char_count\"]} chars')
        print(f'First 100 chars: {sample[\"text\"][:100]}...')
"
        
        echo -e "\n🚀 Starting full pipeline..."
        ./run_full_pipeline.sh
        exit 0
    fi
    
    echo "⏳ Check $i/15 - Still processing... ($(date +%H:%M:%S))"
done

echo "⚠️  Timeout after 7.5 minutes - check manually"
