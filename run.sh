#!/bin/bash
# SparzaFI Quick Start Script

echo "🚀 Starting SparzaFI Platform..."
echo ""

# Activate virtual environment
source .venv/bin/activate

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Run Flask
flask run --port 80
