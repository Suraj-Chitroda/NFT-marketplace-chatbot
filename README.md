# NFT Marketplace Chatbot

Production-grade AI chatbot for NFT marketplace built with Agno framework.

## Features

- 🤖 **Intelligent Agent**: Powered by Groq (Llama 3.3 70B) or OpenAI GPT-4o
- 🎨 **Dynamic HTML Templates**: Returns styled HTML components for NFT displays
- 💾 **Custom Database**: SQLAlchemy-based memory and session management
- 🔧 **Modular Architecture**: Clean separation of concerns (Agent, Tools, Services, DB, HTTP)
- 📦 **Tool Integration**: NFT listing and details tools with filtering/sorting
- 🎯 **Anti-Hallucination**: Strict tool-grounded responses with detailed instructions
- 🔄 **Context Management**: User preferences and conversation history
- 🛡️ **Rate Limiting**: 60 requests/minute per IP (SlowAPI)
- 📊 **Structured Logging**: Request tracking and debugging
- ✅ **Startup Validation**: Fails fast if API keys missing
- 🏷️ **Response Headers**: Returns user/session IDs for tracking

## Architecture

```
nft_chatbot/
├── agent/           # Agno agent, context manager, response parser
├── db/              # SQLAlchemy models, repository
├── models/          # Pydantic schemas for API
├── services/        # Business logic orchestration
├── tools/           # NFT API tools
├── config.py        # Settings management
└── main.py          # FastAPI app

backend/             # Existing NFT API and templates
```

## Setup

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env` and add your API keys:

```bash
# Required: At least one AI provider
GROQ_API_KEY=your_groq_key_here
# OR
OPENAI_API_KEY=your_openai_key_here

# NFT API
NFT_API_BASE=http://localhost:4000
```

### 3. Initialize Database

```bash
python -c "import asyncio; from nft_chatbot.db.database import init_db; asyncio.run(init_db())"
```

## Running

### Start NFT API Backend (Terminal 1)

```bash
cd backend
source ../venv/bin/activate
python api_backend.py
```

### Start Chatbot API (Terminal 2)

```bash
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)  # Load env vars
python agno-agent.py
```

The chatbot will be available at `http://localhost:8000`

## API Usage

### Chat Endpoint

```bash
curl -X POST http://localhost:8000/chat \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "Show me some NFTs",
    "user_id": "user-123",
    "session_id": "optional-session-id"
  }'
```

### Response Format

```json
{
  "session_id": "70bb45b1-90ad-4515-aa04-d40f38f3e3d6",
  "blocks": [
    {
      "type": "text",
      "markdown": "I found 10 NFTs matching your criteria:"
    },
    {
      "type": "html_component",
      "html": "<div class='nft-grid'>...</div>",
      "template": "grid"
    }
  ]
}
```

### Other Endpoints

- `GET /health` - Health check
- `GET /sessions/{user_id}` - Get user's sessions

## Example Queries

- "Show me some NFTs"
- "Find rare NFTs under 5 ETH"
- "Show NFTs from the Meta Legends collection"
- "Tell me about NFT nft-042"
- "I prefer table view" (saves preference)
- "Show more details" (adjusts detail level)

## Database

SQLite database (`nft_chatbot.db`) with 4 tables:

- `users`: User accounts
- `sessions`: Conversation sessions
- `messages`: Chat history
- `memories`: User preferences and learned facts

## Development

### Project Structure

- **Agent Layer**: Agno agent configuration, context building, response parsing
- **Tools Layer**: NFT API integration with template rendering
- **Service Layer**: Chat orchestration (ChatService)
- **DB Layer**: Database operations (Repository pattern)
- **HTTP Layer**: FastAPI endpoints (thin handlers)

### Key Design Decisions

1. **Custom DB over Agno's native**: More control and flexibility
2. **Single Agent + Template Service**: Better performance than multi-agent
3. **Structured Response Blocks**: Clean separation of markdown and HTML
4. **History in System Prompt**: Simpler than message-based history

## Testing

```bash
# Run tests
pytest

# Test chat endpoint
python -m pytest tests/test_chat.py -v
```

## Production Deployment

1. Use PostgreSQL instead of SQLite:
   ```
   DATABASE_URL=postgresql+asyncpg://user:pass@host/db
   ```

2. Set up Alembic migrations:
   ```bash
   alembic init alembic
   alembic revision --autogenerate -m "Initial"
   alembic upgrade head
   ```

3. Use production ASGI server:
   ```bash
   gunicorn nft_chatbot.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

4. Enable CORS for your frontend domain in `.env`

## License

MIT
