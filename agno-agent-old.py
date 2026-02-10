"""
NFT Website Chatbot — Production-grade Agno AI agent with FastAPI.

Features:
- Two tools: NFT list (sort/filter/pagination) and single NFT details
- User + session memory (SQLite); conversation history in context
- Strong instructions to avoid hallucination; multi-tool when needed
- FastAPI /chat with X-User-Id and X-Session-Id for identity
"""

from __future__ import annotations

import logging
import os
import uuid

import dotenv
dotenv.load_dotenv()
from typing import Any, Optional

import requests
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.groq import Groq
from agno.tools import tool

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nft-chatbot")

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Dummy APIs: use DummyJSON "products" as NFTs (see README for alternatives)
NFT_API_BASE = os.getenv("NFT_API_BASE", "https://dummyjson.com").rstrip("/")
# For DummyJSON, list path is /products, single is /products/{id}
NFT_LIST_PATH = os.getenv("NFT_LIST_PATH", "products")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

DB_FILE = os.getenv("AGNO_DB_FILE", "agno.db")
MAX_HISTORY_MESSAGES = int(os.getenv("AGNO_MAX_HISTORY_MESSAGES", "30"))
REQUEST_TIMEOUT = int(os.getenv("NFT_REQUEST_TIMEOUT", "15"))

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------

app = FastAPI(
    title="NFT AI Chatbot API",
    version="1.0.0",
    description="AI chatbot for NFT website: list NFTs with sort/filter, get single NFT details. Uses Agno with user/session memory.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# -----------------------------------------------------------------------------
# Database & session/memory
# -----------------------------------------------------------------------------

db = SqliteDb(db_file=DB_FILE)

# -----------------------------------------------------------------------------
# Model
# -----------------------------------------------------------------------------

model = Groq(
    id=os.getenv("GROQ_MODEL", "openai/gpt-oss-safeguard-20b"),
    temperature=0.1,
    max_tokens=2000,
)

# -----------------------------------------------------------------------------
# Tool input schemas
# -----------------------------------------------------------------------------


class NFTListParams(BaseModel):
    """Parameters for listing NFTs with sorting and filtering."""

    limit: Optional[int] = Field(default=20, ge=1, le=100, description="Number of NFTs per page")
    skip: Optional[int] = Field(default=0, ge=0, description="Number of NFTs to skip (pagination)")
    sort_by: Optional[str] = Field(
        default="id",
        description="Field to sort by: id, title, price, rating, stock, etc.",
    )
    order: Optional[str] = Field(default="asc", description="Sort order: asc or desc")
    category: Optional[str] = Field(
        default=None,
        description="Filter by category slug (e.g. smartphones, laptops). Omit for all.",
    )
    search: Optional[str] = Field(default=None, description="Search query for title/description")


class SingleNFTParams(BaseModel):
    """Parameters for fetching a single NFT by ID."""

    nft_id: str = Field(..., description="The unique NFT ID (e.g. 1, 2, 42)")


# Ensure Pydantic models are fully built before @tool introspects them
NFTListParams.model_rebuild()
SingleNFTParams.model_rebuild()


# -----------------------------------------------------------------------------
# Tools (API calls)
# -----------------------------------------------------------------------------


@tool(
    name="get_nft_list",
    description=(
        "Fetch a paginated list of NFTs with optional sorting and filtering. "
        "Use this when the user asks to browse NFTs, list NFTs, show collections, "
        "filter by category, sort by price/rating, or get the first/next page of results. "
        "Supports: limit, skip (pagination), sort_by (e.g. price, rating, title), order (asc/desc), "
        "category (filter), and search (text search)."
    ),
)
def get_nft_list(params: NFTListParams) -> dict[str, Any]:
    """Call the NFT list API with sorting and filtering."""
    base = f"{NFT_API_BASE}/{NFT_LIST_PATH}"
    limit = params.limit or 20
    skip = params.skip or 0

    if params.category:
        url = f"{NFT_API_BASE}/{NFT_LIST_PATH}/category/{params.category}"
        params_dict = {"limit": limit, "skip": skip}
    elif params.search:
        url = f"{NFT_API_BASE}/{NFT_LIST_PATH}/search"
        params_dict = {"q": params.search, "limit": limit, "skip": skip}
    else:
        url = base
        params_dict = {
            "limit": limit,
            "skip": skip,
            "sortBy": params.sort_by or "id",
            "order": (params.order or "asc").lower(),
        }

    try:
        resp = requests.get(url, params=params_dict, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.exception("NFT list API error: %s", e)
        return {"error": str(e), "products": [], "total": 0}


@tool(
    name="get_single_nft",
    description=(
        "Fetch full details for one NFT by its ID. Use this when the user asks about "
        "a specific NFT (e.g. 'details of NFT 5', 'show me NFT id 42', 'what is the price of NFT 1'). "
        "You must call this tool with the exact nft_id; do not invent IDs. If the user refers to "
        "an NFT from a previous list, use that NFT's id."
    ),
)
def get_single_nft(params: SingleNFTParams) -> dict[str, Any]:
    """Call the single-NFT API."""
    url = f"{NFT_API_BASE}/{NFT_LIST_PATH}/{params.nft_id}"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.exception("Single NFT API error: %s", e)
        return {"error": str(e)}


# -----------------------------------------------------------------------------
# Agent instructions (strong context, no hallucination)
# -----------------------------------------------------------------------------

AGENT_INSTRUCTIONS = """
You are the AI assistant for an NFT marketplace website. You help users discover and inspect NFTs.

## Data and tools
- You have exactly two tools: get_nft_list (list with sort/filter/pagination) and get_single_nft (one NFT by id).
- All NFT data MUST come from these tools. Never invent IDs, prices, titles, or attributes.
- If the user asks for something you cannot do with these tools (e.g. buy, bid), say you can only help browse and show details and suggest they use the website for that.

## When to use which tool
- Browsing, listing, "show NFTs", filter by category, sort by price/rating, pagination → use get_nft_list (and optionally adjust limit, skip, sort_by, order, category, search).
- Details of one specific NFT (by id or "the first one", "the one you just showed") → use get_single_nft with that nft_id.
- You MAY call multiple tools in one turn when needed (e.g. list then details for one item, or list in two different sort orders).

## Context and memory
- Use the conversation history and any stored user/session context. If the user says "the first one" or "that one", refer to the last list you returned and use the correct id for get_single_nft.
- Remember user preferences (e.g. "I like cheap ones") from the conversation and apply them in follow-up tool calls when relevant.

## Response style
- Be concise and professional. Summarize list results (e.g. count, key fields); for single NFT give a short, accurate summary from the API response.
- If an API returns an error, say so clearly and suggest retrying or different filters.
- Do not hallucinate any NFT data; only state what the tools returned.
"""

# -----------------------------------------------------------------------------
# Agent
# -----------------------------------------------------------------------------

nft_agent = Agent(
    name="NFT-Chatbot",
    model=model,
    tools=[get_nft_list, get_single_nft],
    db=db,
    instructions=AGENT_INSTRUCTIONS,
    add_history_to_context=True,
    num_history_messages=MAX_HISTORY_MESSAGES,
    update_memory_on_run=True,
    add_memories_to_context=True,  # required for memories to be injected into prompt across sessions
    markdown=True,
    tool_call_limit=10,
)

# -----------------------------------------------------------------------------
# API models
# -----------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    reply: str


# -----------------------------------------------------------------------------
# Dependencies
# -----------------------------------------------------------------------------


def get_user_id(x_user_id: Optional[str] = Header(None, alias="X-User-Id")) -> str:
    return x_user_id or str(uuid.uuid4())


def get_session_id(x_session_id: Optional[str] = Header(None, alias="X-Session-Id")) -> str:
    return x_session_id or str(uuid.uuid4())


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@app.post("/chat", response_model=ChatResponse)
@limiter.limit("60/minute")
def chat(
    request: Request,
    body: ChatRequest,
    response: Response,
    user_id: str = Depends(get_user_id),
    session_id: str = Depends(get_session_id),
):
    """Send a message and get the assistant reply. Uses user_id and session_id for memory and history.
    For the same user across different sessions, send the same X-User-Id every time so memorie  are recalled."""
    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not set. Configure it and restart.",
        )
    logger.info("Chat request user_id=%s session_id=%s", user_id, session_id)
    try:
        result = nft_agent.run(
            body.message,
            user_id=user_id,
            session_id=session_id,
        )
        response.headers["X-User-Id-Used"] = user_id
        response.headers["X-Session-Id-Used"] = session_id
        return ChatResponse(reply=result.content or "")
    except Exception as e:
        logger.exception("Chat error: %s", e)
        raise HTTPException(status_code=500, detail="Chat processing failed. Please try again.")


@app.get("/health")
def health():
    return {"status": "ok", "service": "nft-chatbot"}


# -----------------------------------------------------------------------------
# Run with uvicorn
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
    )
