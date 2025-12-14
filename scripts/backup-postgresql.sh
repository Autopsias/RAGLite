#!/bin/bash
# PostgreSQL Backup Script
# Creates a backup of the raglite database before risky operations
#
# Usage:
#   ./scripts/backup-postgresql.sh                    # Create timestamped backup
#   ./scripts/backup-postgresql.sh my_backup.sql      # Create named backup
#
# Prevention: Run this before any migrations or destructive operations

set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${1:-${BACKUP_DIR}/postgresql_backup_${TIMESTAMP}.sql}"

# Create backup directory if it doesn't exist
mkdir -p "$(dirname "$BACKUP_FILE")"

echo "=== PostgreSQL Backup Script ==="
echo ""

# Check if PostgreSQL container is running
if ! docker ps | grep -q raglite-postgresql; then
    echo "ERROR: PostgreSQL container 'raglite-postgresql' is not running"
    echo "Start it with: docker-compose up -d postgresql"
    exit 1
fi

# Get current row counts for verification
echo "Current database state:"
docker exec raglite-postgresql psql -U raglite -d raglite -c \
    "SELECT 'financial_tables' as table_name, COUNT(*) as rows FROM financial_tables
     UNION ALL
     SELECT 'financial_chunks', COUNT(*) FROM financial_chunks;" 2>/dev/null || true
echo ""

# Create backup
echo "Creating backup: $BACKUP_FILE"
docker exec raglite-postgresql pg_dump -U raglite -d raglite > "$BACKUP_FILE"

# Verify backup was created
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo ""
    echo "Backup created successfully!"
    echo "  File: $BACKUP_FILE"
    echo "  Size: $BACKUP_SIZE"
    echo ""
    echo "To restore this backup, run:"
    echo "  docker exec -i raglite-postgresql psql -U raglite -d raglite < $BACKUP_FILE"
else
    echo "ERROR: Backup file was not created"
    exit 1
fi
