#!/bin/bash

# CI Database Setup Script
# Fixes database connectivity issues in CI by ensuring proper test databases and users exist
#
# Usage: ./scripts/ci-database-setup.sh
#   - Sets up test databases for both local and CI environments
#   - Creates users and databases with correct permissions
#   - Ensures PostgreSQL on port 5433 is ready for CI pipeline

set -euo pipefail

# Test container configuration
TEST_CONTAINER="raglite-postgresql-test"
TEST_PORT="5433"
TEST_HOST="localhost"

echo "========================================"
echo "🔧 CI Database Setup"
echo "========================================"
echo "Target: PostgreSQL on port $TEST_PORT"

# Function to execute SQL in test container
# FIX: Use raglite_ci credentials that match docker-compose.yml configuration
exec_sql() {
    local sql="$1"
    docker exec "$TEST_CONTAINER" psql -U raglite_ci -d postgres -c "$sql"
}

# Function to check if database exists
db_exists() {
    local db_name="$1"
    docker exec "$TEST_CONTAINER" psql -U raglite_ci -d postgres -c "SELECT 1 FROM pg_database WHERE datname='$db_name'" | grep -q 1
}

# Function to check if user exists
user_exists() {
    local user_name="$1"
    docker exec "$TEST_CONTAINER" psql -U raglite_ci -d postgres -c "SELECT 1 FROM pg_roles WHERE rolname='$user_name'" | grep -q 1
}

# 1. Ensure test PostgreSQL container is running
echo ""
echo "📦 Step 1: Ensure test container is running..."

if ! docker ps --format '{{.Names}}' | grep -q "^${TEST_CONTAINER}$"; then
    echo "Container $TEST_CONTAINER not running, starting..."
    docker compose up -d postgresql-test
    echo "Waiting for PostgreSQL to be ready..."
    sleep 8
else
    echo "✅ Container $TEST_CONTAINER is running"
fi

# 2. Wait for PostgreSQL to be ready
echo ""
echo "🔗 Step 2: Verify PostgreSQL connectivity..."

# FIX: Increased timeout to 30s for CI environments where startup may be slower
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # FIX: Use raglite_ci credentials that match docker-compose.yml
    if docker exec "$TEST_CONTAINER" psql -U raglite_ci -d postgres -c "SELECT 1" > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready (connected in ${RETRY_COUNT}s)"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $((RETRY_COUNT % 5)) -eq 0 ]; then
        echo "Waiting for PostgreSQL... (attempt $RETRY_COUNT/$MAX_RETRIES)"
    fi
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ PostgreSQL not ready after ${MAX_RETRIES}s"
    echo "Container logs:"
    docker logs "$TEST_CONTAINER" --tail 30 || true
    exit 1
fi

# 3. Create users and databases
echo ""
echo "👥 Step 3: Create users and databases..."

# Create raglite_test user/database (for local testing)
if ! user_exists "raglite_test"; then
    echo "Creating user: raglite_test"
    exec_sql "CREATE USER raglite_test WITH PASSWORD 'raglite_test';"
else
    echo "✅ User raglite_test already exists"
fi

if ! db_exists "raglite_test"; then
    echo "Creating database: raglite_test"
    exec_sql "CREATE DATABASE raglite_test OWNER raglite_test;"
else
    echo "✅ Database raglite_test already exists"
fi

# Create raglite_ci user/database (for CI pipeline)
if ! user_exists "raglite_ci"; then
    echo "Creating user: raglite_ci"
    exec_sql "CREATE USER raglite_ci WITH PASSWORD 'raglite_ci';"
else
    echo "✅ User raglite_ci already exists"
fi

if ! db_exists "raglite_ci"; then
    echo "Creating database: raglite_ci"
    exec_sql "CREATE DATABASE raglite_ci OWNER raglite_ci;"
else
    echo "✅ Database raglite_ci already exists"
fi

# 4. Grant permissions
echo ""
echo "🔐 Step 4: Grant database permissions..."

exec_sql "GRANT ALL PRIVILEGES ON DATABASE raglite_test TO raglite_test;"
exec_sql "GRANT ALL PRIVILEGES ON DATABASE raglite_ci TO raglite_ci;"

# Grant schema permissions for table creation
# FIX: Use raglite_ci superuser to grant permissions (it owns the databases)
echo "Granting schema permissions..."
docker exec "$TEST_CONTAINER" psql -U raglite_ci -d raglite_test -c "GRANT ALL ON SCHEMA public TO raglite_test;"
docker exec "$TEST_CONTAINER" psql -U raglite_ci -d raglite_ci -c "GRANT ALL ON SCHEMA public TO raglite_ci;"

echo "✅ Permissions granted"

# 5. Initialize database schemas
echo ""
echo "🏗️  Step 5: Initialize database schemas..."

# Initialize raglite_test schema
echo "Initializing schema for raglite_test..."
if APP_ENV=test POSTGRES_DB=raglite_test POSTGRES_USER=raglite_test POSTGRES_PASSWORD=raglite_test python scripts/init-test-postgresql.py; then
    echo "✅ raglite_test schema initialized"
else
    echo "❌ Failed to initialize raglite_test schema"
fi

# Initialize raglite_ci schema
echo "Initializing schema for raglite_ci..."
if APP_ENV=test CI=true POSTGRES_DB=raglite_ci POSTGRES_USER=raglite_ci POSTGRES_PASSWORD=raglite_ci python scripts/init-test-postgresql.py; then
    echo "✅ raglite_ci schema initialized"
else
    echo "❌ Failed to initialize raglite_ci schema"
fi

# 6. Verify setup
echo ""
echo "✅ Step 6: Verify setup"

echo "Testing raglite_test connection..."
if docker exec "$TEST_CONTAINER" psql -U raglite_test -d raglite_test -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" | grep -q "^[0-9]"; then
    echo "✅ raglite_test: $(docker exec "$TEST_CONTAINER" psql -U raglite_test -d raglite_test -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'") tables"
else
    echo "❌ raglite_test connection failed"
fi

echo "Testing raglite_ci connection..."
if docker exec "$TEST_CONTAINER" psql -U raglite_ci -d raglite_ci -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" | grep -q "^[0-9]"; then
    echo "✅ raglite_ci: $(docker exec "$TEST_CONTAINER" psql -U raglite_ci -d raglite_ci -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'") tables"
else
    echo "❌ raglite_ci connection failed"
fi

echo ""
echo "========================================"
echo "✅ CI Database Setup Complete"
echo "========================================"
echo "Test PostgreSQL: localhost:$TEST_PORT"
echo "Databases: raglite_test, raglite_ci"
echo "Users: raglite_test, raglite_ci"
echo ""
echo "Ready for CI pipeline!"
