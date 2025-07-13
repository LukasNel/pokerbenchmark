#!/bin/bash
#
# Simple script to run the web frontend for the poker benchmark.
#

set -e  # Exit on any error

echo "Starting Poker AI Benchmark Web Interface..."
echo "Open your browser to: http://localhost:8000"
echo "Press Ctrl+C to stop the server"

# Check if uvicorn is available
if ! command -v uvicorn &> /dev/null; then
    echo "Error: uvicorn not found. Please install requirements with: pip install -r requirements.txt"
    exit 1
fi

# Run the uvicorn server
uvicorn web_frontend:app --host 0.0.0.0 --port 8000 --reload