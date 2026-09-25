#!/bin/bash
# LexPilot - Quick Start Script
# Automates setup and startup process

set -e

echo "========================================"
echo "  LexPilot - AI Legal Assistant"
echo "  Quick Start Script"
echo "========================================"
echo ""

# Check Python version
echo "✓ Checking Python version..."
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "  Python version: $python_version"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "✓ Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "✓ Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check .env file
if [ ! -f ".env" ]; then
    echo "✓ Creating .env file from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your API keys!"
    echo "   Required: OPENAI_API_KEY, ANTHROPIC_API_KEY"
    echo ""
    read -p "Press Enter after you've updated .env..."
fi

# Run database migrations (if using database)
echo "✓ Setting up database (if configured)..."
python -c "from src.database import init_database; import asyncio; asyncio.run(init_database())" 2>/dev/null || echo "  (Database setup skipped or failed)"

# Start server
echo ""
echo "========================================"
echo "  Starting LexPilot Server..."
echo "========================================"
echo ""
echo "  API Docs: http://localhost:8000/docs"
echo "  Health:   http://localhost:8000/health"
echo ""
echo "  Press Ctrl+C to stop"
echo ""

python main.py serve --reload
