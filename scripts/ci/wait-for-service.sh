#!/bin/bash
# Wait for Docker service to be ready with exponential backoff
# Usage: wait-for-service.sh SERVICE_TYPE CONTAINER_NAME [MAX_WAIT_SECONDS]
#
# SERVICE_TYPE: postgresql | qdrant
# CONTAINER_NAME: Name of Docker container
# MAX_WAIT_SECONDS: Maximum time to wait (default: 90)

set -e

SERVICE_TYPE="${1:-}"
CONTAINER_NAME="${2:-}"
MAX_WAIT="${3:-90}"

if [ -z "$SERVICE_TYPE" ] || [ -z "$CONTAINER_NAME" ]; then
    echo "❌ Usage: $0 SERVICE_TYPE CONTAINER_NAME [MAX_WAIT_SECONDS]"
    echo "   SERVICE_TYPE: postgresql | qdrant"
    echo "   CONTAINER_NAME: Name of Docker container"
    echo "   MAX_WAIT_SECONDS: Maximum time to wait (default: 90)"
    exit 1
fi

# Validate service type
if [ "$SERVICE_TYPE" != "postgresql" ] && [ "$SERVICE_TYPE" != "qdrant" ]; then
    echo "❌ Invalid SERVICE_TYPE: $SERVICE_TYPE (must be 'postgresql' or 'qdrant')"
    exit 1
fi

# Exponential backoff configuration
BACKOFF_MULTIPLIER=1.5
CURRENT_DELAY=1
TOTAL_WAIT=0

echo "⏳ Waiting for $SERVICE_TYPE ($CONTAINER_NAME) to be ready..."
echo "   Max wait time: ${MAX_WAIT}s"

while [ $TOTAL_WAIT -lt $MAX_WAIT ]; do
    if [ "$SERVICE_TYPE" = "postgresql" ]; then
        # Use pg_isready instead of log parsing
        if docker exec "$CONTAINER_NAME" pg_isready -h localhost -p 5432 -U raglite >/dev/null 2>&1; then
            echo "✅ PostgreSQL ready (waited ${TOTAL_WAIT}s)"

            # Additional validation: ensure database exists and is accessible
            if docker exec "$CONTAINER_NAME" psql -U raglite -d raglite -c "SELECT 1" >/dev/null 2>&1; then
                echo "✅ PostgreSQL database accessible"
                exit 0
            else
                echo "⚠️  PostgreSQL running but database not accessible, retrying..."
            fi
        fi
    elif [ "$SERVICE_TYPE" = "qdrant" ]; then
        # Extract port from container (handle both test and production)
        PORT=$(docker port "$CONTAINER_NAME" 6333/tcp 2>/dev/null | cut -d: -f2 || echo "")

        if [ -z "$PORT" ]; then
            echo "⚠️  Container $CONTAINER_NAME has no port mapping yet, retrying..."
        else
            # Use health endpoint instead of collections list
            if curl -sf "http://localhost:${PORT}/healthz" >/dev/null 2>&1; then
                echo "✅ Qdrant ready on port $PORT (waited ${TOTAL_WAIT}s)"

                # Additional validation: ensure we can list collections
                if curl -sf "http://localhost:${PORT}/collections" >/dev/null 2>&1; then
                    echo "✅ Qdrant API accessible"
                    exit 0
                else
                    echo "⚠️  Qdrant health check passed but API not accessible, retrying..."
                fi
            fi
        fi
    fi

    # Exponential backoff
    sleep "$CURRENT_DELAY"
    TOTAL_WAIT=$((TOTAL_WAIT + CURRENT_DELAY))

    # Calculate next delay (exponential backoff with cap at 10s)
    NEXT_DELAY=$(echo "$CURRENT_DELAY * $BACKOFF_MULTIPLIER" | bc | cut -d. -f1)
    if [ "$NEXT_DELAY" -gt 10 ]; then
        NEXT_DELAY=10
    fi
    CURRENT_DELAY=$NEXT_DELAY

    echo "⏳ Still waiting... (${TOTAL_WAIT}s elapsed, next check in ${CURRENT_DELAY}s)"
done

echo "❌ Timeout waiting for $SERVICE_TYPE ($CONTAINER_NAME) after ${MAX_WAIT}s"
echo ""
echo "Container status:"
docker ps -a --filter "name=$CONTAINER_NAME"
echo ""
echo "Container logs (last 50 lines):"
docker logs "$CONTAINER_NAME" --tail 50 2>&1 || echo "Failed to get logs"
exit 1
