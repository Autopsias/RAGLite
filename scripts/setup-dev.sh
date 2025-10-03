#!/usr/bin/env bash
#
# RAGLite Development Environment Setup Script
#
# Purpose: One-command setup for local development environment
# Usage: ./scripts/setup-dev.sh
#
# This script:
# 1. Checks prerequisites (Python 3.11+, Docker)
# 2. Installs Poetry if not present
# 3. Installs Python dependencies
# 4. Starts Qdrant via Docker Compose
# 5. Initializes Qdrant collection
# 6. Runs validation tests
#

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}===================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}===================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Step 1: Check Prerequisites
print_header "Step 1: Checking Prerequisites"

# Check Python version
print_info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found. Please install Python 3.11+ from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    print_error "Python 3.11+ required. Found: $PYTHON_VERSION"
    exit 1
fi

print_success "Python $PYTHON_VERSION found"

# Check Docker
print_info "Checking Docker..."
if ! command -v docker &> /dev/null; then
    print_error "Docker not found. Please install from https://www.docker.com/products/docker-desktop"
    exit 1
fi

print_success "Docker $(docker --version | cut -d' ' -f3 | tr -d ',') found"

# Check Docker Compose
print_info "Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose not found. Please install Docker Desktop or docker-compose plugin"
    exit 1
fi

print_success "Docker Compose found"

# Step 2: Install Poetry
print_header "Step 2: Installing Poetry (if needed)"

if command -v poetry &> /dev/null; then
    POETRY_VERSION=$(poetry --version | cut -d' ' -f3)
    print_success "Poetry $POETRY_VERSION already installed"
else
    print_info "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -

    # Add Poetry to PATH for this session
    export PATH="$HOME/.local/bin:$PATH"

    if command -v poetry &> /dev/null; then
        print_success "Poetry installed successfully"
    else
        print_error "Poetry installation failed. Please install manually: https://python-poetry.org/docs/#installation"
        exit 1
    fi
fi

# Step 3: Install Python Dependencies
print_header "Step 3: Installing Python Dependencies"

print_info "Configuring Poetry to create virtualenv in project..."
poetry config virtualenvs.in-project true

print_info "Installing dependencies (this may take a few minutes)..."
if poetry install --no-interaction; then
    print_success "Dependencies installed successfully"
else
    print_error "Dependency installation failed"
    exit 1
fi

# Step 4: Environment Variables
print_header "Step 4: Checking Environment Variables"

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        print_info "Creating .env from .env.example..."
        cp .env.example .env
        print_warning ".env created - Please add your ANTHROPIC_API_KEY before running the server"
        print_info "Edit .env and add: ANTHROPIC_API_KEY=sk-ant-..."
    else
        print_warning ".env.example not found - you may need to configure environment variables manually"
    fi
else
    print_success ".env file already exists"
fi

# Step 5: Start Qdrant
print_header "Step 5: Starting Qdrant Vector Database"

print_info "Starting Qdrant via Docker Compose..."
if docker-compose up -d; then
    print_success "Qdrant started successfully"
else
    print_error "Failed to start Qdrant. Check Docker is running and try: docker-compose up -d"
    exit 1
fi

# Wait for Qdrant to be ready
print_info "Waiting for Qdrant to be ready..."
RETRY=0
MAX_RETRIES=30

while [ $RETRY -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:6333/collections > /dev/null 2>&1; then
        print_success "Qdrant is ready"
        break
    fi
    RETRY=$((RETRY + 1))
    echo -n "."
    sleep 1
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    print_error "Qdrant failed to start within 30 seconds"
    print_info "Check logs with: docker-compose logs qdrant"
    exit 1
fi

# Step 6: Initialize Qdrant Collection (if init script exists)
print_header "Step 6: Initializing Qdrant Collection"

if [ -f "scripts/init-qdrant.py" ]; then
    print_info "Running Qdrant initialization script..."
    if poetry run python scripts/init-qdrant.py; then
        print_success "Qdrant collection initialized"
    else
        print_warning "Qdrant initialization script failed (may already be initialized)"
    fi
else
    print_warning "scripts/init-qdrant.py not found - skip collection initialization"
    print_info "You may need to run this manually in Story 1.6"
fi

# Step 7: Install Pre-commit Hooks
print_header "Step 7: Installing Pre-commit Hooks"

if [ -f ".pre-commit-config.yaml" ]; then
    print_info "Installing pre-commit hooks..."
    if poetry run pre-commit install; then
        print_success "Pre-commit hooks installed"
    else
        print_warning "Pre-commit hook installation failed (non-critical)"
    fi
else
    print_warning ".pre-commit-config.yaml not found - skipping pre-commit setup"
fi

# Step 8: Run Validation Tests
print_header "Step 8: Running Validation Tests"

print_info "Running pytest to validate setup..."
if poetry run pytest --version > /dev/null 2>&1; then
    print_success "pytest is working"

    # Run actual tests if they exist
    if [ -d "raglite/tests" ]; then
        print_info "Running test suite..."
        if poetry run pytest -v; then
            print_success "All tests passed"
        else
            print_warning "Some tests failed - this may be expected if Week 0 code is incomplete"
        fi
    else
        print_info "No tests found yet (expected in Week 1)"
    fi
else
    print_error "pytest not working correctly"
    exit 1
fi

# Final Summary
print_header "Setup Complete! 🎉"

echo -e "${GREEN}Development environment is ready.${NC}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Edit .env and add your ANTHROPIC_API_KEY"
echo "  2. Start development server: poetry run python -m raglite.main"
echo "  3. Run tests: poetry run pytest"
echo "  4. Format code: poetry run black raglite/"
echo "  5. Lint code: poetry run ruff check raglite/"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  poetry shell                  # Activate virtual environment"
echo "  poetry run pytest             # Run tests"
echo "  poetry run pytest --cov       # Run tests with coverage"
echo "  docker-compose logs qdrant    # View Qdrant logs"
echo "  docker-compose stop           # Stop services"
echo "  docker-compose down           # Stop and remove containers"
echo ""
echo -e "${GREEN}Happy coding! 🚀${NC}"
