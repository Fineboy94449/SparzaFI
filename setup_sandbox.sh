#!/bin/bash

# SparzaFI Sandbox Setup Script
# This script helps you quickly set up a sandbox environment for testing

echo "🧪 SparzaFI Sandbox Setup"
echo "=========================="
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "📦 ngrok not found. Installing..."

    # Install ngrok
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
    sudo apt update && sudo apt install ngrok -y

    echo "✅ ngrok installed!"
    echo ""
    echo "⚠️  IMPORTANT: You need to authenticate ngrok"
    echo "   1. Sign up at: https://dashboard.ngrok.com/signup (free)"
    echo "   2. Get your auth token from the dashboard"
    echo "   3. Run: ngrok config add-authtoken YOUR_TOKEN_HERE"
    echo ""
    read -p "Press Enter once you've authenticated ngrok..."
else
    echo "✅ ngrok already installed"
fi

echo ""
echo "🔧 Setting up database..."

# Check if database exists
if [ ! -f "sparzafi.db" ]; then
    echo "Creating fresh database..."
    python3 database_seed.py
    python3 seed_thandi_data.py
else
    echo "Database already exists"
    read -p "Do you want to reset it with fresh demo data? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm sparzafi.db
        python3 database_seed.py
        python3 seed_thandi_data.py
        echo "✅ Database reset with demo data"
    fi
fi

echo ""
echo "🎯 Sandbox is ready!"
echo ""
echo "To start your sandbox environment:"
echo ""
echo "Option 1: ngrok (Public Internet Access)"
echo "  Terminal 1: python3 app.py"
echo "  Terminal 2: ngrok http 5000"
echo "  Then share the ngrok URL with testers"
echo ""
echo "Option 2: Local Network Only"
echo "  python3 app.py"
echo "  Share this URL: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "📋 Demo Accounts:"
echo "  Admin:    admin@sparzafi.com / adminpass"
echo "  Seller:   thandi@sparzafi.com / sellerpass"
echo "  Buyer:    buyer1@test.com / buyerpass"
echo "  Deliverer: sipho.driver@sparzafi.com / driverpass"
echo ""
echo "📚 For more options, see SANDBOX_SETUP.md"
echo ""
