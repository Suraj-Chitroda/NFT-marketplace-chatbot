"""
Repository pattern for database CRUD operations.
"""

from typing import Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from nft_chatbot.db.models import User, Session, Message, Memory


class ChatRepository:
    """Repository for chat-related database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # --- User Operations ---
    
    async def get_or_create_user(self, external_id: str) -> User:
        """Get existing user or create new one."""
        result = await self.db.execute(
            select(User).where(User.external_id == external_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(external_id=external_id)
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
        
        return user
    
    # --- Session Operations ---
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        result = await self.db.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalar_one_or_none()
    
    async def create_session(self, user_id: str, title: Optional[str] = None) -> Session:
        """Create new conversation session."""
        session = Session(user_id=user_id, title=title, state={})
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session
    
    async def update_session_state(self, session_id: str, state: dict) -> None:
        """Update session state."""
        session = await self.get_session(session_id)
        if session:
            session.state = {**(session.state or {}), **state}
            session.updated_at = datetime.utcnow()
            await self.db.commit()
    
    async def get_user_sessions(self, user_id: str) -> List[Session]:
        """Get all sessions for a user."""
        result = await self.db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(desc(Session.updated_at))
        )
        return list(result.scalars().all())
    
    # --- Message Operations ---
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        content_type: str = "markdown",
        tool_calls: Optional[dict] = None,
        token_count: Optional[int] = None
    ) -> Message:
        """Add message to session."""
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            content_type=content_type,
            tool_calls=tool_calls,
            token_count=token_count
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message
    
    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 20
    ) -> List[Message]:
        """Get recent messages for a session."""
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        messages = list(result.scalars().all())
        return list(reversed(messages))  # Return chronological order
    
    # --- Memory Operations ---
    
    async def get_user_memories(self, user_id: str) -> List[Memory]:
        """Get all memories for a user."""
        result = await self.db.execute(
            select(Memory).where(Memory.user_id == user_id)
        )
        return list(result.scalars().all())
    
    async def upsert_memory(
        self,
        user_id: str,
        memory_type: str,
        key: str,
        value: str,
        confidence: float = 1.0
    ) -> Memory:
        """Create or update a memory."""
        result = await self.db.execute(
            select(Memory).where(
                Memory.user_id == user_id,
                Memory.key == key
            )
        )
        memory = result.scalar_one_or_none()
        
        if memory:
            memory.value = value
            memory.confidence = confidence
            memory.updated_at = datetime.utcnow()
        else:
            memory = Memory(
                user_id=user_id,
                memory_type=memory_type,
                key=key,
                value=value,
                confidence=confidence
            )
            self.db.add(memory)
        
        await self.db.commit()
        await self.db.refresh(memory)
        return memory
    
    async def delete_memory(self, user_id: str, key: str) -> bool:
        """Delete a specific memory."""
        result = await self.db.execute(
            select(Memory).where(
                Memory.user_id == user_id,
                Memory.key == key
            )
        )
        memory = result.scalar_one_or_none()
        if memory:
            await self.db.delete(memory)
            await self.db.commit()
            return True
        return False

    async def delete_memories_by_type(self, user_id: str, memory_type: str) -> int:
        """Delete all memories of a given type for a user. Returns count deleted."""
        result = await self.db.execute(
            select(Memory).where(
                Memory.user_id == user_id,
                Memory.memory_type == memory_type
            )
        )
        memories = list(result.scalars().all())
        for m in memories:
            await self.db.delete(m)
        if memories:
            await self.db.commit()
        return len(memories)
