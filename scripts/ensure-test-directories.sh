#!/bin/bash
# Ensure test directories exist for CI/CD pipeline
# This prevents Qdrant collection creation failures

set -euo pipefail

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Directories required for tests
DIRECTORIES=(
    "$PROJECT_ROOT/data"
    "$PROJECT_ROOT/data/qdrant"
    "$PROJECT_ROOT/qdrant_storage"
    "$PROJECT_ROOT/qdrant_storage_test"
)

echo "Ensuring test directories exist..."

for dir in "${DIRECTORIES[@]}"; do
    if [[ ! -d "$dir" ]]; then
        echo "Creating directory: $dir"
        mkdir -p "$dir"
    else
        echo "Directory exists: $dir"
    fi
done

echo "✅ All test directories are ready"
