#!/bin/bash
# Add 'raglite' label to RAGLite runners for project isolation
# This ensures RAGLite CI jobs ONLY run on RAGLite runners, not other project runners

set -e

RUNNER_1_DIR="$HOME/github-runners/runner-1"
RUNNER_2_DIR="$HOME/github-runners/runner-2"
REPO_URL="https://github.com/Autopsias/RAGLite"

echo "=========================================="
echo "RAGLite Runner Label Configuration"
echo "=========================================="
echo ""
echo "This script will add the 'raglite' label to your two RAGLite runners."
echo "This ensures that CI jobs for this project ONLY run on these specific runners."
echo ""
echo "Runners to configure:"
echo "  1. raglite-runner-1 ($RUNNER_1_DIR)"
echo "  2. raglite-runner-2 ($RUNNER_2_DIR)"
echo ""

# Check if runners exist
if [ ! -d "$RUNNER_1_DIR" ]; then
    echo "❌ Error: Runner 1 directory not found: $RUNNER_1_DIR"
    exit 1
fi

if [ ! -d "$RUNNER_2_DIR" ]; then
    echo "❌ Error: Runner 2 directory not found: $RUNNER_2_DIR"
    exit 1
fi

echo "⚠️  WARNING: This will reconfigure your runners with the following labels:"
echo "   - self-hosted (default)"
echo "   - macOS (default)"
echo "   - ARM64 (default)"
echo "   - raglite (CUSTOM - for project isolation)"
echo ""
echo "You will need your GitHub Personal Access Token (PAT) for reconfiguration."
echo ""
read -p "Do you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
read -p "Enter your GitHub Personal Access Token (PAT): " -s GITHUB_PAT
echo ""

if [ -z "$GITHUB_PAT" ]; then
    echo "❌ Error: PAT cannot be empty"
    exit 1
fi

echo ""
echo "=========================================="
echo "Step 1: Stopping and uninstalling services"
echo "=========================================="

cd "$RUNNER_1_DIR"
echo "Stopping raglite-runner-1 service..."
sudo ./svc.sh stop || echo "Runner 1 already stopped"
echo "Uninstalling raglite-runner-1 service..."
sudo ./svc.sh uninstall || echo "Service already uninstalled"

cd "$RUNNER_2_DIR"
echo "Stopping raglite-runner-2 service..."
sudo ./svc.sh stop || echo "Runner 2 already stopped"
echo "Uninstalling raglite-runner-2 service..."
sudo ./svc.sh uninstall || echo "Service already uninstalled"

sleep 3

echo ""
echo "=========================================="
echo "Step 2: Removing existing configurations"
echo "=========================================="

cd "$RUNNER_1_DIR"
echo "Removing raglite-runner-1 configuration..."
./config.sh remove --token "$GITHUB_PAT"

cd "$RUNNER_2_DIR"
echo "Removing raglite-runner-2 configuration..."
./config.sh remove --token "$GITHUB_PAT"

echo ""
echo "=========================================="
echo "Step 3: Reconfiguring with 'raglite' label"
echo "=========================================="

cd "$RUNNER_1_DIR"
echo "Configuring raglite-runner-1..."
./config.sh \
    --url "$REPO_URL" \
    --token "$GITHUB_PAT" \
    --name "raglite-runner-1" \
    --labels "raglite" \
    --work "_work" \
    --replace

cd "$RUNNER_2_DIR"
echo "Configuring raglite-runner-2..."
./config.sh \
    --url "$REPO_URL" \
    --token "$GITHUB_PAT" \
    --name "raglite-runner-2" \
    --labels "raglite" \
    --work "_work" \
    --replace

echo ""
echo "=========================================="
echo "Step 4: Installing and starting services"
echo "=========================================="

cd "$RUNNER_1_DIR"
echo "Installing raglite-runner-1 service..."
sudo ./svc.sh install
echo "Starting raglite-runner-1..."
sudo ./svc.sh start

cd "$RUNNER_2_DIR"
echo "Installing raglite-runner-2 service..."
sudo ./svc.sh install
echo "Starting raglite-runner-2..."
sudo ./svc.sh start

echo ""
echo "=========================================="
echo "✅ SUCCESS!"
echo "=========================================="
echo ""
echo "Both runners have been reconfigured with the 'raglite' label."
echo ""
echo "Configured labels:"
echo "  - self-hosted"
echo "  - macOS"
echo "  - ARM64"
echo "  - raglite ⭐ (CUSTOM)"
echo ""
echo "Next steps:"
echo "  1. Update your CI workflow to use: runs-on: [self-hosted, raglite]"
echo "  2. Commit and push the workflow changes"
echo "  3. Test with a CI run to verify isolation"
echo ""
echo "To verify runners are running:"
echo "  ps aux | grep Runner.Listener | grep raglite"
echo ""
