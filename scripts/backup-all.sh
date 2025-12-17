#!/bin/bash
# Full Database Backup Script
# Creates backups of both PostgreSQL and Qdrant production databases
#
# Usage:
#   ./scripts/backup-all.sh                    # Create timestamped backups
#   ./scripts/backup-all.sh --prefix mybackup  # Create backups with custom prefix
#
# Output:
#   ./backups/postgresql_backup_YYYYMMDD_HHMMSS.sql
#   ./backups/qdrant_backup_YYYYMMDD_HHMMSS.snapshot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PREFIX="${1:-backup}"

mkdir -p "$BACKUP_DIR"

echo "============================================================"
echo "RAGLite Full Database Backup"
echo "============================================================"
echo "Timestamp: $(date)"
echo "Backup directory: $BACKUP_DIR"
echo ""

# Backup PostgreSQL
echo "------------------------------------------------------------"
echo "[1/2] Backing up PostgreSQL..."
echo "------------------------------------------------------------"
"${SCRIPT_DIR}/backup-postgresql.sh" "${BACKUP_DIR}/postgresql_${PREFIX}_${TIMESTAMP}.sql"

echo ""

# Backup Qdrant
echo "------------------------------------------------------------"
echo "[2/2] Backing up Qdrant..."
echo "------------------------------------------------------------"
"${SCRIPT_DIR}/backup-qdrant.sh" "${BACKUP_DIR}/qdrant_${PREFIX}_${TIMESTAMP}.snapshot"

echo ""
echo "============================================================"
echo "BACKUP COMPLETE"
echo "============================================================"
echo ""
echo "Files created:"
ls -lh "${BACKUP_DIR}"/*${TIMESTAMP}* 2>/dev/null || echo "  (check backup directory)"
echo ""
echo "Total backup size:"
du -sh "$BACKUP_DIR"
