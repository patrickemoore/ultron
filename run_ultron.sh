#!/bin/bash
set -e

# Check for API key
if [ -z "$OPENAI_API_KEY" ]; then
  echo "Error: OPENAI_API_KEY is not set. Please export it before running."
  exit 1
fi

# Run render.py from the current directory
python3 "$(dirname "$0")/ultron.py"
