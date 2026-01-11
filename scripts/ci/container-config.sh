#!/usr/bin/env bash
# CI Container Port Configuration - Single Source of Truth
# This file defines ALL container port assignments for CI test infrastructure
#
# CRITICAL: Production ports 6333/5432 are NEVER used by CI
# All CI variants use separate ports to prevent production access

# Note: No strict error handling here - designed to be sourced by other scripts

# ============================================================
# Port Mapping by Variant
# ============================================================

# Qdrant ports (maps internal 6333 to external port)
declare -A QDRANT_PORTS=(
    ["test"]="6335"
    ["agentic"]="6337"
    ["discovery"]="6339"
    ["burnin"]="6340"
)

# PostgreSQL ports (maps internal 5432 to external port)
declare -A POSTGRES_PORTS=(
    ["test"]="5433"
    ["agentic"]="5438"
    ["discovery"]="5434"
    ["burnin"]="5435"
)

# ============================================================
# PRODUCTION PORTS - NEVER USED BY CI
# ============================================================

readonly PRODUCTION_QDRANT_PORT="6333"
readonly PRODUCTION_POSTGRES_PORT="5432"

# Validate no CI variant uses production ports (disable nounset for array iteration)
set +u
for variant in "${!QDRANT_PORTS[@]}"; do
    if [[ "${QDRANT_PORTS[$variant]}" == "$PRODUCTION_QDRANT_PORT" ]]; then
        echo "❌ CRITICAL: Variant '$variant' uses PRODUCTION Qdrant port!" >&2
        exit 1
    fi
done

for variant in "${!POSTGRES_PORTS[@]}"; do
    if [[ "${POSTGRES_PORTS[$variant]}" == "$PRODUCTION_POSTGRES_PORT" ]]; then
        echo "❌ CRITICAL: Variant '$variant' uses PRODUCTION PostgreSQL port!" >&2
        exit 1
    fi
done
set -u

# ============================================================
# Database Credentials - SINGLE SOURCE OF TRUTH
# ============================================================
# CRITICAL: All CI jobs MUST source credentials from here
# Never hardcode credentials in workflow files or inline scripts

readonly CI_POSTGRES_USER="raglite_ci"
readonly CI_POSTGRES_PASSWORD="raglite_ci"
readonly CI_POSTGRES_DB="raglite_ci"

# ============================================================
# Resource Limits
# ============================================================

readonly QDRANT_MEMORY="1g"
readonly QDRANT_CPU_LIMIT="2.0"
readonly POSTGRES_MEMORY="512m"
readonly POSTGRES_SHM="256m"
readonly POSTGRES_CPU_LIMIT="1.0"

# ============================================================
# Health Check Configuration
# ============================================================

readonly HEALTH_CHECK_TIMEOUT=90           # Max seconds to wait for startup
readonly HEALTH_CHECK_INTERVAL=2           # Seconds between checks
readonly BACKOFF_MULTIPLIER=1.5            # Exponential backoff multiplier
readonly QDRANT_READY_TIMEOUT=30           # Qdrant-specific ready timeout
readonly POSTGRES_READY_TIMEOUT=30         # PostgreSQL-specific ready timeout

# ============================================================
# Container Names
# ============================================================

# Get container name for variant
get_qdrant_container_name() {
    local variant="$1"
    echo "raglite-qdrant-${variant}"
}

get_postgres_container_name() {
    local variant="$1"
    echo "raglite-postgresql-${variant}"
}

# ============================================================
# Port Retrieval Functions
# ============================================================

get_qdrant_port() {
    local variant="$1"
    if [[ -z "${QDRANT_PORTS[$variant]:-}" ]]; then
        echo "❌ Unknown variant: $variant" >&2
        echo "   Valid variants: ${!QDRANT_PORTS[*]}" >&2
        return 1
    fi
    echo "${QDRANT_PORTS[$variant]}"
}

get_postgres_port() {
    local variant="$1"
    if [[ -z "${POSTGRES_PORTS[$variant]:-}" ]]; then
        echo "❌ Unknown variant: $variant" >&2
        echo "   Valid variants: ${!POSTGRES_PORTS[*]}" >&2
        return 1
    fi
    echo "${POSTGRES_PORTS[$variant]}"
}

# ============================================================
# Validation Functions
# ============================================================

validate_variant() {
    local variant="$1"
    local valid_variants="${!QDRANT_PORTS[*]}"

    if [[ -z "${QDRANT_PORTS[$variant]:-}" ]]; then
        echo "❌ Invalid variant: '$variant'" >&2
        echo "   Valid variants: $valid_variants" >&2
        return 1
    fi

    return 0
}

# Check if port is in use (macOS compatible)
is_port_in_use() {
    local port="$1"
    if lsof -Pi :${port} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Validate no production ports are in use by CI
validate_no_production_ports() {
    local errors=0

    if is_port_in_use "$PRODUCTION_QDRANT_PORT"; then
        echo "⚠️  WARNING: Production Qdrant port $PRODUCTION_QDRANT_PORT is in use!" >&2
        ((errors++))
    fi

    if is_port_in_use "$PRODUCTION_POSTGRES_PORT"; then
        echo "⚠️  WARNING: Production PostgreSQL port $PRODUCTION_POSTGRES_PORT is in use!" >&2
        ((errors++))
    fi

    return $errors
}

# ============================================================
# Environment Export Functions
# ============================================================

# Export ports for a variant as environment variables
export_variant_ports() {
    local variant="$1"
    local output_file="${2:-.ci-env}"

    validate_variant "$variant" || return 1

    local qdrant_port=$(get_qdrant_port "$variant")
    local postgres_port=$(get_postgres_port "$variant")

    # Export to file for GitHub Actions (can be sourced)
    cat > "$output_file" <<EOF
# CI Container Configuration for variant: $variant
# Generated by container-config.sh - SINGLE SOURCE OF TRUTH

# Ports
export QDRANT_PORT=$qdrant_port
export POSTGRES_PORT=$postgres_port

# Container names
export QDRANT_CONTAINER=$(get_qdrant_container_name "$variant")
export POSTGRES_CONTAINER=$(get_postgres_container_name "$variant")

# Database credentials (from centralized config)
export POSTGRES_USER=$CI_POSTGRES_USER
export POSTGRES_PASSWORD=$CI_POSTGRES_PASSWORD
export POSTGRES_DB=$CI_POSTGRES_DB

# Variant identifier
export VARIANT=$variant
EOF

    # Also export to current shell if running interactively
    if [[ -t 1 ]]; then
        source "$output_file"
        echo "✅ Exported ports for variant '$variant':"
        echo "   QDRANT_PORT=$qdrant_port"
        echo "   POSTGRES_PORT=$postgres_port"
    fi

    return 0
}

# ============================================================
# Credential Getter Functions
# ============================================================

get_postgres_user() {
    echo "$CI_POSTGRES_USER"
}

get_postgres_password() {
    echo "$CI_POSTGRES_PASSWORD"
}

get_postgres_db() {
    echo "$CI_POSTGRES_DB"
}

# ============================================================
# Credential Validation Function
# ============================================================

# Validate that CI workflow credentials match centralized config
validate_ci_credentials() {
    local workflow_file="${1:-.github/workflows/ci.yml}"
    local errors=0

    if [[ ! -f "$workflow_file" ]]; then
        echo "⚠️  Warning: Workflow file not found: $workflow_file" >&2
        return 0  # Don't fail if file doesn't exist (may be called from wrong dir)
    fi

    # Check for hardcoded credentials that don't match centralized config
    if grep -q "user='raglite'" "$workflow_file" 2>/dev/null; then
        echo "❌ ERROR: Found hardcoded 'raglite' user in $workflow_file" >&2
        echo "   Expected: '$CI_POSTGRES_USER'" >&2
        ((errors++))
    fi

    if grep -q "password='raglite'" "$workflow_file" 2>/dev/null; then
        echo "❌ ERROR: Found hardcoded 'raglite' password in $workflow_file" >&2
        echo "   Expected: '$CI_POSTGRES_PASSWORD'" >&2
        ((errors++))
    fi

    if grep -q "database='raglite_test'" "$workflow_file" 2>/dev/null; then
        echo "❌ ERROR: Found hardcoded 'raglite_test' database in $workflow_file" >&2
        echo "   Expected: '$CI_POSTGRES_DB'" >&2
        ((errors++))
    fi

    if [[ $errors -gt 0 ]]; then
        echo "" >&2
        echo "💡 FIX: Update credentials in $workflow_file to use:" >&2
        echo "   user='$CI_POSTGRES_USER'" >&2
        echo "   password='$CI_POSTGRES_PASSWORD'" >&2
        echo "   database='$CI_POSTGRES_DB'" >&2
        return 1
    fi

    echo "✅ CI workflow credentials are consistent with centralized config"
    return 0
}

# ============================================================
# Usage Information
# ============================================================

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    cat <<'USAGE'
CI Container Configuration
===========================

This script provides port and resource configuration for CI test containers.

Usage:
  source scripts/ci/container-config.sh
  export_variant_ports <variant> [output_file]

Variants:
  test       - Unit/integration tests (ports 6335/5433)
  agentic    - Agentic workflow tests (ports 6337/5438)
  discovery  - Discovery tests (ports 6339/5434)
  burnin     - Burn-in tests (ports 6340/5435)

Examples:
  # Export ports for test variant
  source scripts/ci/container-config.sh
  export_variant_ports test

  # Get specific port
  source scripts/ci/container-config.sh
  get_qdrant_port test  # Returns: 6335

  # Validate variant
  source scripts/ci/container-config.sh
  validate_variant test && echo "Valid"

Production Protection:
  - Production ports 6333/5432 are NEVER used by CI
  - All variants validated at load time
  - Port conflict detection included

USAGE
fi
