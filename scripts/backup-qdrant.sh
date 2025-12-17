#!/bin/bash
# Qdrant Backup Script
# Creates a snapshot backup of the financial_docs collection
#
# Usage:
#   ./scripts/backup-qdrant.sh                         # Create timestamped backup
#   ./scripts/backup-qdrant.sh my_backup.snapshot      # Create named backup
#
# Prevention: Run this before any migrations or destructive operations

set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
QDRANT_HOST="${QDRANT_HOST:-localhost}"
QDRANT_PORT="${QDRANT_PORT:-6333}"
COLLECTION="financial_docs"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "=== Qdrant Backup Script ==="
echo ""

# Check if Qdrant is running
if ! curl -s "http://${QDRANT_HOST}:${QDRANT_PORT}/collections/${COLLECTION}" > /dev/null 2>&1; then
    echo "ERROR: Qdrant collection '${COLLECTION}' is not accessible at ${QDRANT_HOST}:${QDRANT_PORT}"
    echo "Start it with: docker-compose up -d qdrant"
    exit 1
fi

# Get current collection stats
echo "Current collection state:"
STATS=$(curl -s "http://${QDRANT_HOST}:${QDRANT_PORT}/collections/${COLLECTION}")
POINTS=$(echo "$STATS" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['points_count'])" 2>/dev/null || echo "unknown")
echo "  Collection: ${COLLECTION}"
echo "  Points (vectors): ${POINTS}"
echo ""

# Create snapshot
echo "Creating snapshot..."
SNAPSHOT_RESPONSE=$(curl -s -X POST "http://${QDRANT_HOST}:${QDRANT_PORT}/collections/${COLLECTION}/snapshots" -H "Content-Type: application/json")

SNAPSHOT_NAME=$(echo "$SNAPSHOT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['name'])" 2>/dev/null)
SNAPSHOT_SIZE=$(echo "$SNAPSHOT_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['size'])" 2>/dev/null)

if [ -z "$SNAPSHOT_NAME" ]; then
    echo "ERROR: Failed to create snapshot"
    echo "Response: $SNAPSHOT_RESPONSE"
    exit 1
fi

echo "  Snapshot created: ${SNAPSHOT_NAME}"
echo ""

# Download snapshot
BACKUP_FILE="${1:-${BACKUP_DIR}/qdrant_backup_${TIMESTAMP}.snapshot}"
echo "Downloading snapshot to: ${BACKUP_FILE}"

curl -s -o "$BACKUP_FILE" "http://${QDRANT_HOST}:${QDRANT_PORT}/collections/${COLLECTION}/snapshots/${SNAPSHOT_NAME}"

# Verify backup was created
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo ""
    echo "Backup created successfully!"
    echo "  File: $BACKUP_FILE"
    echo "  Size: $BACKUP_SIZE"
    echo "  Points: ${POINTS}"
    echo ""
    echo "To restore this backup:"
    echo "  1. Stop Qdrant"
    echo "  2. Copy snapshot to Qdrant snapshots directory"
    echo "  3. Use Qdrant recovery API:"
    echo "     curl -X PUT \"http://localhost:6333/collections/${COLLECTION}/snapshots/recover\" \\"
    echo "       -H \"Content-Type: application/json\" \\"
    echo "       -d '{\"location\": \"file:///path/to/snapshot\"}'"
else
    echo "ERROR: Backup file was not created"
    exit 1
fi
