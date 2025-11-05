#!/bin/bash
# Simple approach: Reconfigure runners with --replace flag
# This adds the 'raglite' label without removing existing config

set -e

RUNNER_1_DIR="$HOME/github-runners/runner-1"
RUNNER_2_DIR="$HOME/github-runners/runner-2"
REPO_URL="https://github.com/Autopsias/RAGLite"

echo "=========================================="
echo "RAGLite Runner Label - Simple Method"
echo "=========================================="
echo ""
echo "This will reconfigure your runners WITH the existing config"
echo "using the --replace flag to add the 'raglite' label."
echo ""

read -p "Enter your GitHub Personal Access Token (PAT): " -s GITHUB_PAT
echo ""

if [ -z "$GITHUB_PAT" ]; then
    echo "❌ Error: PAT cannot be empty"
    exit 1
fi

echo ""
echo "Reconfiguring raglite-runner-1..."
cd "$RUNNER_1_DIR"
./config.sh \
    --url "$REPO_URL" \
    --token "$GITHUB_PAT" \
    --name "raglite-runner-1" \
    --labels "raglite" \
    --work "_work" \
    --replace \
    --unattended

echo ""
echo "Reconfiguring raglite-runner-2..."
cd "$RUNNER_2_DIR"
./config.sh \
    --url "$REPO_URL" \
    --token "$GITHUB_PAT" \
    --name "raglite-runner-2" \
    --labels "raglite" \
    --work "_work" \
    --replace \
    --unattended

echo ""
echo "=========================================="
echo "✅ SUCCESS!"
echo "=========================================="
echo ""
echo "Runners reconfigured with 'raglite' label."
echo ""
echo "Verify in GitHub UI:"
echo "  https://github.com/Autopsias/RAGLite/settings/actions/runners"
echo ""
