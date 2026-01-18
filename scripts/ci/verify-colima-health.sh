#!/usr/bin/env bash
# Colima VM Health Verification
# Detects zombie states, memory exhaustion, and network corruption
#
# Usage: verify-colima-health.sh <profile>
# Exit codes: 0=healthy, 1=zombie, 2=memory, 3=network, 4=other

set -euo pipefail

PROFILE="${1:-}"
if [[ -z "$PROFILE" ]]; then
    echo "❌ Usage: verify-colima-health.sh <profile>" >&2
    exit 4
fi

echo "=== Verifying Colima VM health: $PROFILE ==="

# Check if profile is running
if ! colima status -p "$PROFILE" 2>/dev/null | grep -q "colima is running"; then
    echo "❌ Profile '$PROFILE' is not running"
    exit 4
fi

# Check Docker daemon responsiveness (zombie detection)
COLIMA_SOCKET="$HOME/.colima/${PROFILE}/docker.sock"
export DOCKER_HOST="unix://$COLIMA_SOCKET"

echo "Checking Docker daemon responsiveness..."
if ! timeout 5 docker info &> /dev/null; then
    echo "❌ ZOMBIE STATE: Socket exists but daemon unresponsive"
    echo "   Root cause: VM memory exhaustion or QEMU deadlock"
    exit 1
fi
echo "✅ Docker daemon is responsive"

# Check memory usage (prevention of OOM)
echo "Checking VM memory usage..."
DOCKER_MEM_INFO=$(docker info 2>/dev/null | grep "Total Memory" || echo "")
if [[ -n "$DOCKER_MEM_INFO" ]]; then
    echo "  $DOCKER_MEM_INFO"

    # Extract memory percentage if available
    MEM_PERCENT=$(echo "$DOCKER_MEM_INFO" | grep -oP '\d+(?=%)' || echo "")
    if [[ -n "$MEM_PERCENT" ]] && [[ $MEM_PERCENT -gt 90 ]]; then
        echo "⚠️  HIGH MEMORY USAGE: ${MEM_PERCENT}%"
        echo "   Risk: Container OOM kills"
    fi
fi

# Check network connectivity (Lima corruption detection)
echo "Checking network connectivity..."
if ! docker run --rm hello-world > /dev/null 2>&1; then
    echo "❌ NETWORK CORRUPTION: Container cannot access network"
    echo "   Root cause: Lima network state corruption"
    echo "   Fix: rm -rf ~/.colima/_lima/_networks && colima restart"
    exit 3
fi
echo "✅ Network connectivity OK"

# Check for zombie processes
echo "Checking for zombie processes..."
ZOMBIE_COUNT=$(ps aux | grep -c "defunct" || echo "0")
if [[ $ZOMBIE_COUNT -gt 10 ]]; then
    echo "⚠️  HIGH ZOMBIE COUNT: ${ZOMBIE_COUNT} defunct processes"
    echo "   Risk: Process table exhaustion"
fi

echo ""
echo "=== Health Summary ==="
echo "Profile: $PROFILE"
echo "Status: Healthy"
echo "Socket: $COLIMA_SOCKET"
echo "Docker: Responsive"
echo "Network: OK"
echo ""
echo "✅ VM is healthy"

exit 0
