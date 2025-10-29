#!/bin/bash
# Final runner configuration script - Run this with your PAT
# Usage: ./configure-runners-final.sh <YOUR_GITHUB_PAT>

if [ -z "$1" ]; then
    echo "❌ Error: Please provide your GitHub PAT as argument"
    echo "Usage: ./configure-runners-final.sh <YOUR_GITHUB_PAT>"
    exit 1
fi

GITHUB_PAT="$1"
REPO_URL="https://github.com/Autopsias/RAGLite"

echo "=========================================="
echo "Configuring RAGLite Runners"
echo "=========================================="
echo ""

# Configure runner-1
echo "Step 1/4: Configuring raglite-runner-1..."
cd ~/github-runners/runner-1 || exit 1
./config.sh \
    --url "$REPO_URL" \
    --token "$GITHUB_PAT" \
    --name "raglite-runner-1" \
    --labels "raglite" \
    --work "_work" \
    --unattended

if [ $? -ne 0 ]; then
    echo "❌ Failed to configure runner-1"
    exit 1
fi

echo ""
echo "Step 2/4: Configuring raglite-runner-2..."
cd ~/github-runners/runner-2 || exit 1
./config.sh \
    --url "$REPO_URL" \
    --token "$GITHUB_PAT" \
    --name "raglite-runner-2" \
    --labels "raglite" \
    --work "_work" \
    --unattended

if [ $? -ne 0 ]; then
    echo "❌ Failed to configure runner-2"
    exit 1
fi

echo ""
echo "Step 3/4: Installing and starting raglite-runner-1..."
cd ~/github-runners/runner-1 || exit 1
./svc.sh install
./svc.sh start

echo ""
echo "Step 4/4: Installing and starting raglite-runner-2..."
cd ~/github-runners/runner-2 || exit 1
./svc.sh install
./svc.sh start

echo ""
echo "=========================================="
echo "✅ SUCCESS!"
echo "=========================================="
echo ""
echo "Verifying runners..."
ps aux | grep "Runner.Listener" | grep -E "runner-1|runner-2" | grep -v grep

echo ""
echo "Check labels in .runner files..."
cat ~/github-runners/runner-1/.runner | grep -E "agentName|gitHubUrl"
cat ~/github-runners/runner-2/.runner | grep -E "agentName|gitHubUrl"

echo ""
echo "Next: Verify in GitHub UI that runners have 'raglite' label:"
echo "  https://github.com/Autopsias/RAGLite/settings/actions/runners"
echo ""
