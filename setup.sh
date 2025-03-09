#!/bin/bash
set -e

# ...existing code...

# Install dependencies
echo "Installing dependencies..."
pip install -r "$(dirname "$0")/requirements.txt"
echo "Setup complete!"
