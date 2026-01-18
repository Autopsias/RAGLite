#!/usr/bin/env bash
# Emergency Colima VM Stop
# Forces shutdown of CI Colima profiles when normal shutdown fails
#
# Usage: colima-emergency-stop.sh [--force]
# Options:
#   --force    Kill QEMU processes (use when VM is completely stuck)

set -euo pipefail

FORCE_KILL=false
if [[ "${1:-}" == "--force" ]]; then
    FORCE_KILL=true
fi

echo "=== Emergency Colima VM Stop ==="
echo ""

# List of CI Colima profiles
CI_PROFILES=("ci-postgresql" "ci-other")

for PROFILE in "${CI_PROFILES[@]}"; do
    echo "Stopping profile: $PROFILE"

    # Try normal shutdown first
    if colima stop -p "$PROFILE" -f 2>/dev/null; then
        echo "✅ Stopped $PROFILE (normal shutdown)"
    else
        echo "⚠️  Normal shutdown failed for $PROFILE"

        # Force delete profile
        if colima delete -p "$PROFILE" -f 2>/dev/null; then
            echo "✅ Deleted $PROFILE (force delete)"
        else
            echo "❌ Failed to delete $PROFILE"

            # If --force flag, kill QEMU processes
            if [[ "$FORCE_KILL" == "true" ]]; then
                echo "🔪 Force killing QEMU processes for $PROFILE..."
                pkill -9 -f "qemu-system.*$PROFILE" 2>/dev/null && echo "  Killed QEMU" || true
            fi
        fi
    fi
    echo ""
done

# Clean up Lima network state (root cause of many issues)
echo "Cleaning up Lima network state..."
if rm -rf "$HOME/.colima/_lima/_networks"; then
    echo "✅ Removed Lima network state"
else
    echo "⚠️  Failed to remove Lima network state"
fi

# Clean up startup locks
echo "Cleaning up startup locks..."
if rm -rf "$HOME/.colima-startup-locks"; then
    echo "✅ Removed startup locks"
else
    echo "⚠️  Failed to remove startup locks"
fi

echo ""
echo "=== Summary ==="
echo "Colima profiles:"
colima list 2>/dev/null || echo "  (none running)"
echo ""
echo "✅ Emergency stop complete"
