#!/bin/bash
# CashFlow Optimizer Agent - Setup Script
# This script validates the environment and creates necessary directories

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "CashFlow Optimizer Agent - Setup"
echo "========================================"
echo ""

# Track errors
ERRORS=0

# -----------------------------------------------------------------------------
# Check required tools
# -----------------------------------------------------------------------------
echo "Checking required tools..."

# Check for Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "  ${GREEN}✓${NC} Node.js installed: ${NODE_VERSION}"
else
    echo -e "  ${RED}✗${NC} Node.js not found"
    echo "    Install from: https://nodejs.org/"
    ERRORS=$((ERRORS + 1))
fi

# Check for npx
if command -v npx &> /dev/null; then
    NPX_VERSION=$(npx --version)
    echo -e "  ${GREEN}✓${NC} npx installed: ${NPX_VERSION}"
else
    echo -e "  ${RED}✗${NC} npx not found"
    echo "    npx should come with Node.js. Try reinstalling Node.js."
    ERRORS=$((ERRORS + 1))
fi

# Check for Python (optional, for database setup)
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "  ${GREEN}✓${NC} Python installed: ${PYTHON_VERSION}"
else
    echo -e "  ${YELLOW}!${NC} Python3 not found (optional, needed for database setup)"
fi

echo ""

# -----------------------------------------------------------------------------
# Create necessary directories
# -----------------------------------------------------------------------------
echo "Creating directories..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create directories if they don't exist
for dir in data reports config src; do
    if [ -d "$dir" ]; then
        echo -e "  ${GREEN}✓${NC} $dir/ exists"
    else
        mkdir -p "$dir"
        echo -e "  ${GREEN}✓${NC} $dir/ created"
    fi
done

echo ""

# -----------------------------------------------------------------------------
# Validate config file
# -----------------------------------------------------------------------------
echo "Validating configuration..."

CONFIG_FILE="config/mcp_config.json"

if [ -f "$CONFIG_FILE" ]; then
    echo -e "  ${GREEN}✓${NC} Config file exists: $CONFIG_FILE"

    # Validate JSON syntax
    if command -v python3 &> /dev/null; then
        if python3 -c "import json; json.load(open('$CONFIG_FILE'))" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Config JSON is valid"
        else
            echo -e "  ${RED}✗${NC} Config JSON is invalid"
            ERRORS=$((ERRORS + 1))
        fi
    elif command -v node &> /dev/null; then
        if node -e "require('./$CONFIG_FILE')" 2>/dev/null; then
            echo -e "  ${GREEN}✓${NC} Config JSON is valid"
        else
            echo -e "  ${RED}✗${NC} Config JSON is invalid"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo -e "  ${YELLOW}!${NC} Could not validate JSON (no python3 or node)"
    fi
else
    echo -e "  ${RED}✗${NC} Config file not found: $CONFIG_FILE"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# -----------------------------------------------------------------------------
# Check database
# -----------------------------------------------------------------------------
echo "Checking database..."

DB_FILE="data/cash_logistics.db"

if [ -f "$DB_FILE" ]; then
    DB_SIZE=$(ls -lh "$DB_FILE" | awk '{print $5}')
    echo -e "  ${GREEN}✓${NC} Database exists: $DB_FILE ($DB_SIZE)"
else
    echo -e "  ${YELLOW}!${NC} Database not found: $DB_FILE"
    echo "    Run: python3 src/setup_database.py"
fi

echo ""

# -----------------------------------------------------------------------------
# Check environment variables
# -----------------------------------------------------------------------------
echo "Checking environment..."

if [ -f ".env" ]; then
    echo -e "  ${GREEN}✓${NC} .env file exists"

    # Source .env to check variables
    set -a
    source .env 2>/dev/null || true
    set +a

    if [ -n "$SLACK_BOT_TOKEN" ]; then
        echo -e "  ${GREEN}✓${NC} SLACK_BOT_TOKEN is set"
    else
        echo -e "  ${YELLOW}!${NC} SLACK_BOT_TOKEN not set (required for Slack alerts)"
    fi

    if [ -n "$SLACK_DEFAULT_CHANNEL" ]; then
        echo -e "  ${GREEN}✓${NC} SLACK_DEFAULT_CHANNEL: $SLACK_DEFAULT_CHANNEL"
    else
        echo -e "  ${YELLOW}!${NC} SLACK_DEFAULT_CHANNEL not set (will use default)"
    fi
else
    echo -e "  ${YELLOW}!${NC} .env file not found"
    echo "    Copy .env.example to .env and configure"
fi

echo ""

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo "========================================"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}Setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Copy .env.example to .env and configure Slack credentials"
    echo "  2. Ensure the database is populated (python3 src/setup_database.py)"
    echo "  3. Start the CashFlow Optimizer agent"
else
    echo -e "${RED}Setup found $ERRORS error(s)${NC}"
    echo ""
    echo "Please fix the errors above before proceeding."
    exit 1
fi
echo "========================================"
