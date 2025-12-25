#!/bin/bash
# Development Environment Startup Script
# Ensures production databases are running with correct volume mounts
# Run this when starting a new development session

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "RAGLite Development Environment Startup"
echo "=========================================="
echo "Project: $PROJECT_DIR"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if container has correct mount
check_mount() {
    local container=$1
    local expected_path=$2

    if ! docker ps -q -f name="^${container}$" 2>/dev/null | grep -q .; then
        return 1  # Container not running
    fi

    local mount_source=$(docker inspect "$container" --format='{{range .Mounts}}{{.Source}}{{end}}' 2>/dev/null)

    if [[ "$mount_source" == *"$expected_path"* ]]; then
        return 0  # Mount is correct
    else
        return 2  # Wrong mount
    fi
}

# Function to recreate container with correct mount
recreate_container() {
    local service=$1
    echo -e "${YELLOW}Recreating $service with correct mounts...${NC}"

    # Stop and remove old container
    docker stop "raglite-$service" 2>/dev/null || true
    docker rm "raglite-$service" 2>/dev/null || true

    # Start fresh via docker-compose
    cd "$PROJECT_DIR"
    docker-compose up -d "$service"

    echo -e "${GREEN}$service recreated${NC}"
}

# Check and fix Qdrant
echo "Checking Qdrant..."
if check_mount "raglite-qdrant" "$PROJECT_DIR/qdrant_storage"; then
    echo -e "${GREEN}Qdrant: Mount OK${NC}"
elif [ $? -eq 1 ]; then
    echo -e "${YELLOW}Qdrant: Not running - starting...${NC}"
    cd "$PROJECT_DIR" && docker-compose up -d qdrant
    echo -e "${GREEN}Qdrant: Started${NC}"
else
    echo -e "${RED}Qdrant: WRONG MOUNT - recreating...${NC}"
    recreate_container "qdrant"
fi

# Check and fix PostgreSQL
echo ""
echo "Checking PostgreSQL..."
if check_mount "raglite-postgresql" "$PROJECT_DIR/postgresql_data"; then
    echo -e "${GREEN}PostgreSQL: Mount OK${NC}"
elif [ $? -eq 1 ]; then
    echo -e "${YELLOW}PostgreSQL: Not running - starting...${NC}"
    cd "$PROJECT_DIR" && docker-compose up -d postgresql
    echo -e "${GREEN}PostgreSQL: Started${NC}"
else
    echo -e "${RED}PostgreSQL: WRONG MOUNT - recreating...${NC}"
    recreate_container "postgresql"
fi

# Wait for services to be ready
echo ""
echo "Waiting for services to be ready..."

# Wait for Qdrant
echo -n "Qdrant: "
MAX_WAIT=30
for i in $(seq 1 $MAX_WAIT); do
    if curl -sf http://localhost:6333/healthz > /dev/null 2>&1; then
        echo -e "${GREEN}Ready${NC}"
        break
    fi
    if [ $i -eq $MAX_WAIT ]; then
        echo -e "${RED}Timeout${NC}"
    fi
    sleep 1
done

# Wait for PostgreSQL
echo -n "PostgreSQL: "
for i in $(seq 1 $MAX_WAIT); do
    if docker exec raglite-postgresql pg_isready -U raglite > /dev/null 2>&1; then
        echo -e "${GREEN}Ready${NC}"
        break
    fi
    if [ $i -eq $MAX_WAIT ]; then
        echo -e "${RED}Timeout${NC}"
    fi
    sleep 1
done

# Verify data is accessible
echo ""
echo "Verifying data access..."

# Check Qdrant collections
QDRANT_VECTORS=$(curl -sf http://localhost:6333/collections/financial_docs 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('result',{}).get('points_count',0))" 2>/dev/null || echo "0")
echo "Qdrant vectors: $QDRANT_VECTORS"

# Check PostgreSQL rows
PG_ROWS=$(docker exec raglite-postgresql psql -U raglite -d raglite -t -c "SELECT COUNT(*) FROM financial_tables" 2>/dev/null | tr -d ' ' || echo "0")
echo "PostgreSQL rows: $PG_ROWS"

echo ""
echo "=========================================="
if [ "$QDRANT_VECTORS" -gt 0 ] && [ "$PG_ROWS" -gt 0 ]; then
    echo -e "${GREEN}Development environment ready!${NC}"
    echo "MCP server can now access production data."
else
    echo -e "${YELLOW}Warning: Databases may be empty or need restore${NC}"
    echo "Run backup restore if needed:"
    echo "  ./scripts/backup-all.sh  # Create new backup"
    echo "  # Or restore from existing backup"
fi
echo "=========================================="
