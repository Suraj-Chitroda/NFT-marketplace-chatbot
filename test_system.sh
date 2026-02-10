#!/bin/bash
# System test script for NFT Chatbot

set -e

echo "🔍 Testing NFT Marketplace Chatbot System"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run: python -m venv venv"
    exit 1
fi

# Activate venv
source venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ .env file not found"
    exit 1
fi

echo "✅ Environment loaded"
echo ""

# Test 1: Database
echo "📊 Test 1: Database Connection"
python -c "import asyncio; from nft_chatbot.db.database import init_db; asyncio.run(init_db()); print('✅ Database OK')" || exit 1
echo ""

# Test 2: NFT API
echo "🎨 Test 2: NFT API (port 4000)"
if curl -s http://localhost:4000/health > /dev/null 2>&1; then
    echo "✅ NFT API is running"
else
    echo "⚠️  NFT API not running. Start with: cd backend && python api_backend.py"
fi
echo ""

# Test 3: Chat API
echo "🤖 Test 3: Chat API (port 8000)"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Chat API is running"
    echo ""
    
    # Test 4: Chat Endpoint
    echo "💬 Test 4: Chat Endpoint"
    response=$(curl -s -X POST http://localhost:8000/chat \
      -H "Content-Type: application/json" \
      -d '{"message": "Hello", "user_id": "test-user"}')
    
    if echo "$response" | grep -q "session_id"; then
        echo "✅ Chat endpoint OK"
        echo "Response preview:"
        echo "$response" | python -m json.tool | head -20
    else
        echo "❌ Chat endpoint failed"
        echo "$response"
    fi
else
    echo "⚠️  Chat API not running. Start with: ./start_chatbot.sh"
fi

echo ""
echo "=========================================="
echo "🎉 Testing complete!"
