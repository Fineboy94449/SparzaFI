#!/bin/bash
# Install SparzaFI Sandbox CLI as a global command

echo "🚀 Installing SparzaFI Sandbox CLI..."
echo ""

# Get the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_PATH="$SCRIPT_DIR/sandbox.py"

# Add alias to bashrc
ALIAS_LINE="alias sparzafitest1='python3 $CLI_PATH'"

# Check if alias already exists
if grep -q "alias sparzafitest1=" ~/.bashrc; then
    echo "✓ Alias already exists in ~/.bashrc"
    # Update it
    sed -i '/alias sparzafitest1=/d' ~/.bashrc
    echo "$ALIAS_LINE" >> ~/.bashrc
    echo "✓ Updated alias in ~/.bashrc"
else
    echo "$ALIAS_LINE" >> ~/.bashrc
    echo "✓ Added alias to ~/.bashrc"
fi

# Also add to zshrc if it exists
if [ -f ~/.zshrc ]; then
    if grep -q "alias sparzafitest1=" ~/.zshrc; then
        echo "✓ Alias already exists in ~/.zshrc"
        sed -i '/alias sparzafitest1=/d' ~/.zshrc
        echo "$ALIAS_LINE" >> ~/.zshrc
        echo "✓ Updated alias in ~/.zshrc"
    else
        echo "$ALIAS_LINE" >> ~/.zshrc
        echo "✓ Added alias to ~/.zshrc"
    fi
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "To use the CLI, run:"
echo ""
echo "  source ~/.bashrc"
echo "  sparzafitest1"
echo ""
echo "Or simply open a new terminal and type: sparzafitest1"
echo ""
