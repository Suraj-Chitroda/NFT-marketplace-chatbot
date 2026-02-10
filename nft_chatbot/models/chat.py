"""
Pydantic models for chat API.
Request/response schemas for structured communication.
"""

from typing import List, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Chat request from client."""
    message: str
    user_id: str
    session_id: Optional[str] = None


class ContentBlock(BaseModel):
    """Individual content block in response."""
    type: str  # "text" | "html_component"
    markdown: Optional[str] = None
    html: Optional[str] = None
    template: Optional[str] = None  # "grid" | "table" | "details"


class ChatResponse(BaseModel):
    """Structured chat response."""
    session_id: str
    blocks: List[ContentBlock]


class SessionInfo(BaseModel):
    """Session summary for listing."""
    id: str
    title: Optional[str]
    created_at: str
    message_count: int
    is_active: bool
