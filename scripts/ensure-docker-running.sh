#!/bin/bash
#
# Ensure Docker Daemon is Running
#
# Purpose: Check if Docker daemon is running and start Docker Desktop if needed
# Usage: ./scripts/ensure-docker-running.sh
#
# This script:
# 1. Checks if Docker daemon is accessible
# 2. Attempts to start Docker Desktop if not running (macOS)
# 3. Waits for Docker to be ready
# 4. Exits with appropriate status codes

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Docker Daemon Availability Check${NC}"
echo -e "${BLUE}=========================================${NC}"

# Check if Docker command exists
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker command not found${NC}"
    echo -e "${YELLOW}Please install Docker Desktop from https://www.docker.com/products/docker-desktop${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker command found: $(which docker)${NC}"

# Check if Docker daemon is running
if docker info &> /dev/null; then
    echo -e "${GREEN}✅ Docker daemon is already running${NC}"
    docker version | head -10
    exit 0
fi

echo -e "${YELLOW}⚠️  Docker daemon is not running${NC}"

# Check for Colima first (if Docker socket points to Colima)
if [[ "$DOCKER_HOST" == *"colima"* ]] || [[ -S "$HOME/.colima/default/docker.sock" ]]; then
    echo -e "${BLUE}Detected Colima configuration${NC}"

    # Check if colima command exists
    if command -v colima &> /dev/null; then
        echo -e "${BLUE}Attempting to start Colima...${NC}"
        colima start

        # Wait for Docker daemon to be ready (max 60 seconds)
        MAX_WAIT=60
        WAIT_COUNT=0

        while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
            if docker info &> /dev/null; then
                echo -e "${GREEN}✅ Docker daemon is now running via Colima (took ${WAIT_COUNT}s)${NC}"
                docker version | head -10
                exit 0
            fi

            if [ $((WAIT_COUNT % 10)) -eq 0 ] && [ $WAIT_COUNT -gt 0 ]; then
                echo -e "${BLUE}Still waiting for Docker daemon... (${WAIT_COUNT}s/${MAX_WAIT}s)${NC}"
            fi

            sleep 1
            WAIT_COUNT=$((WAIT_COUNT + 1))
        done

        echo -e "${RED}❌ Colima did not start Docker daemon within ${MAX_WAIT} seconds${NC}"
        echo -e "${YELLOW}Try: brew services restart colima${NC}"
        exit 1
    else
        echo -e "${YELLOW}⚠️  Colima socket detected but colima command not found${NC}"
        echo -e "${YELLOW}Install with: brew install colima${NC}"
        exit 1
    fi
fi

# Attempt to start Docker Desktop (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "${BLUE}Attempting to start Docker Desktop...${NC}"

    # Check if Docker.app exists
    if [ -d "/Applications/Docker.app" ]; then
        open -a Docker
        echo -e "${BLUE}Docker Desktop starting...${NC}"

        # Wait for Docker daemon to be ready (max 60 seconds)
        MAX_WAIT=60
        WAIT_COUNT=0

        while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
            if docker info &> /dev/null; then
                echo -e "${GREEN}✅ Docker daemon is now running (took ${WAIT_COUNT}s)${NC}"
                docker version | head -10
                exit 0
            fi

            if [ $((WAIT_COUNT % 10)) -eq 0 ] && [ $WAIT_COUNT -gt 0 ]; then
                echo -e "${BLUE}Still waiting for Docker daemon... (${WAIT_COUNT}s/${MAX_WAIT}s)${NC}"
            fi

            sleep 1
            WAIT_COUNT=$((WAIT_COUNT + 1))
        done

        echo -e "${RED}❌ Docker daemon did not start within ${MAX_WAIT} seconds${NC}"
        echo -e "${YELLOW}Please start Docker Desktop manually and try again${NC}"
        exit 1
    else
        echo -e "${RED}❌ Docker.app not found in /Applications/${NC}"
        echo -e "${YELLOW}Please install Docker Desktop from https://www.docker.com/products/docker-desktop${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Automatic Docker start only supported on macOS${NC}"
    echo -e "${YELLOW}Please start Docker daemon manually and try again${NC}"
    exit 1
fi
