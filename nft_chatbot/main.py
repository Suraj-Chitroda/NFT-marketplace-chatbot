"""
FastAPI application - HTTP handling ONLY.
All business logic delegated to ChatService.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from nft_chatbot.config import settings
from nft_chatbot.db.database import get_db, init_db
from nft_chatbot.db.repository import ChatRepository
from nft_chatbot.services.chat_service import ChatService
from nft_chatbot.models.chat import ChatRequest, ChatResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nft-chatbot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB and validate configuration on startup."""
    # Validate API keys
    if not settings.groq_api_key and not settings.openai_api_key:
        logger.error("No AI API key configured! Set GROQ_API_KEY or OPENAI_API_KEY in .env")
        raise ValueError("No AI API key configured. Set GROQ_API_KEY or OPENAI_API_KEY in .env")
    
    logger.info("Initializing database...")
    await init_db()
    logger.info("NFT Chatbot API started successfully")
    logger.info(f"Using model: {'Groq' if settings.groq_api_key else 'OpenAI'}")
    
    yield
    
    logger.info("NFT Chatbot API shutting down")


app = FastAPI(
    title="NFT Marketplace Chatbot API",
    version="1.0.0",
    description="AI-powered chatbot for NFT marketplace with structured responses",
    lifespan=lifespan
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Routes (thin handlers) ---

@app.post("/chat", response_model=ChatResponse)
@limiter.limit("60/minute")
async def chat(
    request: Request,  # Required by SlowAPI for rate limiting
    body: ChatRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Chat with the NFT marketplace assistant.
    
    Returns structured response with separated markdown and HTML blocks.
    Rate limit: 60 requests per minute per IP.
    """
    logger.info(f"Chat request: user_id={body.user_id}, session_id={body.session_id}")
    
    try:
        service = ChatService(ChatRepository(db))
        session_id, blocks = await service.process_message(
            user_id=body.user_id,
            session_id=body.session_id,
            message=body.message
        )
        
        # Add tracking headers
        response.headers["X-User-Id-Used"] = body.user_id
        response.headers["X-Session-Id-Used"] = session_id
        
        logger.info(f"Chat response: session_id={session_id}, blocks={len(blocks)}")
        return ChatResponse(session_id=session_id, blocks=blocks)
        
    except Exception as e:
        logger.exception(f"Chat error for user {body.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Chat processing failed. Please try again.")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "nft-chatbot",
        "version": "1.0.0"
    }


@app.get("/sessions/{user_id}")
async def get_user_sessions(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get all sessions for a user."""
    repo = ChatRepository(db)
    user = await repo.get_or_create_user(user_id)
    sessions = await repo.get_user_sessions(user.id)
    
    return {
        "user_id": user_id,
        "sessions": [
            {
                "id": session.id,
                "title": session.title,
                "is_active": session.is_active,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            }
            for session in sessions
        ]
    }


# --- Entry point ---

def main():
    """Run the chatbot server."""
    import uvicorn
    uvicorn.run(
        "nft_chatbot.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
