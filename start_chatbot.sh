#!/bin/bash
# Startup script for NFT Chatbot

set -e

# Load .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Activate virtual environment
source venv/bin/activate

# Start the chatbot
echo "🚀 Starting NFT Chatbot on http://localhost:8000"
python agno-agent.py
