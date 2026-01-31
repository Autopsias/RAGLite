#!/bin/bash
# RAGLite Environment Configuration Checker
# Run this before any database operations to detect configuration conflicts
#
# Usage: ./scripts/check-env.sh

echo "RAGLite Environment Check"
echo "=============================="
echo ""

ISSUES=0

# Check for test environment override
if [ "$APP_ENV" = "test" ] && [ -z "$GITHUB_ACTIONS" ] && [ -z "$CI" ]; then
    echo "WARNING: APP_ENV=test (shell override)"
    echo "   -> This overrides .env file. Production uses: APP_ENV=production"
    ISSUES=$((ISSUES+1))
fi

if [ "$POSTGRES_PORT" = "5433" ] && [ -z "$GITHUB_ACTIONS" ]; then
    echo "WARNING: POSTGRES_PORT=5433 (test database port)"
    echo "   -> Production uses: POSTGRES_PORT=5432"
    ISSUES=$((ISSUES+1))
fi

if [ "$POSTGRES_DB" = "raglite_ci" ] || [ "$POSTGRES_DB" = "raglite_test" ]; then
    echo "WARNING: POSTGRES_DB=$POSTGRES_DB (test database)"
    echo "   -> Production uses: POSTGRES_DB=raglite"
    ISSUES=$((ISSUES+1))
fi

if [ "$TESTING" = "true" ]; then
    echo "WARNING: TESTING=true (test mode flag)"
    ISSUES=$((ISSUES+1))
fi

if [ $ISSUES -gt 0 ]; then
    echo ""
    echo "--------------------------------------------"
    echo "To clear test environment, run:"
    echo ""
    echo "  unset APP_ENV POSTGRES_PORT POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD TESTING"
    echo ""
    echo "Or start a new terminal session."
    echo "--------------------------------------------"
else
    echo "No shell overrides detected - .env file values will be used"
fi

echo ""
echo ".env file values:"
if [ -f ".env" ]; then
    grep -E "^(APP_ENV|POSTGRES_PORT|POSTGRES_DB)=" .env 2>/dev/null | sed 's/^/   /'
else
    echo "   .env file not found in current directory"
fi

echo ""
echo "Effective configuration (what Python will use):"
python3 -c "
from raglite.shared.config import get_settings
s = get_settings()
print(f'   APP_ENV={s.app_env}')
print(f'   POSTGRES_PORT={s.postgres_port}')
print(f'   POSTGRES_DB={s.postgres_db}')
print(f'   QDRANT_PORT={s.qdrant_port}')
" 2>/dev/null || echo "   (Python check failed - run: uv sync)"

exit $ISSUES
