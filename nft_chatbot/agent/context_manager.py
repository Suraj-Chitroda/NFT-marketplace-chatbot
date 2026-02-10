"""
Context manager - builds conversation context from custom database.
"""

import json
from typing import List

from nft_chatbot.db.repository import ChatRepository
from nft_chatbot.db.models import Message, Memory
from nft_chatbot.models.memory_keys import (
    MEMORY_TYPE_PERSONAL,
    MEMORY_TYPE_PREFERENCE,
    MEMORY_TYPE_INTENT,
    MEMORY_TYPE_BEHAVIOR,
)


class ContextManager:
    """Builds conversation context for the agent from custom DB."""
    
    def __init__(self, repository: ChatRepository):
        self.repo = repository
    
    async def build_context(
        self,
        user_id: str,
        session_id: str,
        max_history: int = 10
    ) -> dict:
        """
        Build complete context for agent run.
        
        Returns:
            {
                "history": [...],  # Formatted conversation history
                "memories": str,   # User preferences/facts as string
                "session_state": {...}  # Current session state
            }
        """
        # Get conversation history
        messages = await self.repo.get_conversation_history(session_id, limit=max_history)
        history = self._format_history(messages)
        
        # Get user memories
        memories = await self.repo.get_user_memories(user_id)
        formatted_memories = self._format_memories(memories)
        
        # Get session state
        session = await self.repo.get_session(session_id)
        session_state = session.state if session else {}
        
        return {
            "history": history,
            "memories": formatted_memories,
            "session_state": session_state
        }
    
    def _format_history(self, messages: List[Message]) -> List[dict]:
        """Format messages for agent context. Expands blocks_json into readable text."""
        result = []
        for msg in messages:
            if msg.role not in ("user", "assistant"):
                continue
            content = msg.content or ""
            if getattr(msg, "content_type", None) == "blocks_json":
                try:
                    blocks = json.loads(content)
                    parts = []
                    for b in blocks if isinstance(blocks, list) else []:
                        md = (b.get("markdown") or "").strip()
                        htd = (b.get("html_tools_data") or "").strip()
                        if md:
                            parts.append(md)
                        if htd:
                            parts.append(htd)
                    content = "\n\n".join(parts) if parts else content
                except (json.JSONDecodeError, TypeError):
                    pass
            result.append({"role": msg.role, "content": content})
        return result
    
    def _format_memories(self, memories: List[Memory]) -> str:
        """Format memories by type: personal details, preferences, intents."""
        if not memories:
            return ""
        
        by_type: dict = {
            MEMORY_TYPE_PERSONAL: [],
            MEMORY_TYPE_PREFERENCE: [],
            MEMORY_TYPE_INTENT: [],
            MEMORY_TYPE_BEHAVIOR: [],
        }
        for mem in memories:
            if mem.memory_type in by_type:
                by_type[mem.memory_type].append((mem.key, mem.value))
            else:
                by_type[MEMORY_TYPE_PREFERENCE].append((mem.key, mem.value))
        
        sections = []
        if by_type[MEMORY_TYPE_PERSONAL]:
            sections.append("## User Personal Details (use when addressing the user):")
            for k, v in by_type[MEMORY_TYPE_PERSONAL]:
                sections.append(f"- {k}: {v}")
        if by_type[MEMORY_TYPE_PREFERENCE]:
            sections.append("## User Preferences (page/response format, styling):")
            for k, v in by_type[MEMORY_TYPE_PREFERENCE]:
                sections.append(f"- {k}: {v}")
        if by_type[MEMORY_TYPE_INTENT] or by_type[MEMORY_TYPE_BEHAVIOR]:
            sections.append("## User Intents & Behavior (tailor suggestions):")
            for k, v in by_type[MEMORY_TYPE_INTENT] + by_type[MEMORY_TYPE_BEHAVIOR]:
                sections.append(f"- {k}: {v}")
        
        return "\n".join(sections) if sections else ""
    
    def build_system_prompt(
        self,
        base_instructions: str,
        memories: str,
        session_state: dict,
        history: List[dict] = None
    ) -> str:
        """Combine base instructions with user context."""
        parts = [base_instructions]
        
        if memories:
            parts.append(memories)
        
        state_str = "\n## Current Session State:\n"
        state_str += "- view_type: infer from user query — e.g. 'list of 5 NFTs', 'show as list' → table; otherwise default grid; do not ask user to confirm)\n"
        session_state = session_state or {}
        nft_list = session_state.get("nft_list") or []
        collection_list = session_state.get("collection_list") or []
        if nft_list:
            state_str += "\n**Last NFTs listed in this session (use these for get_nft_details when user says 'the first one', 'that one', 'the third', 'the Crypto Kings one', etc.):**\n"
            for i, nft in enumerate(nft_list[:20], 1):
                nid = nft.get("id") if isinstance(nft, dict) else None
                name = nft.get("name", "?") if isinstance(nft, dict) else "?"
                coll = nft.get("collection", "") if isinstance(nft, dict) else ""
                state_str += f"- #{i}: {nid} — {name} ({coll})\n"
            state_str += "Use the **id** value as nft_id in get_nft_details. Never ask the user for NFT ID.\n"
        if collection_list:
            state_str += "\n**Last collections listed in this session (use collection name for list_nfts when user says 'NFTs from the first collection', 'that collection', etc.):**\n"
            for i, col in enumerate(collection_list[:20], 1):
                cname = col.get("name", "?") if isinstance(col, dict) else "?"
                count = col.get("nft_count", 0) if isinstance(col, dict) else 0
                state_str += f"- #{i}: {cname} ({count} NFTs)\n"
        last_list_params = session_state.get("last_list_params")
        if last_list_params and isinstance(last_list_params, dict):
            prev_skip = last_list_params.get("skip", 0) or 0
            prev_limit = last_list_params.get("limit", 10) or 10
            next_skip = prev_skip + prev_limit
            parts_list = [f"limit={prev_limit}", f"skip={prev_skip}", f"sort_by={last_list_params.get('sort_by', 'tokenId')}", f"order={last_list_params.get('order', 'asc')}"]
            if last_list_params.get("collection"):
                parts_list.append(f"collection={last_list_params.get('collection')!r}")
            if last_list_params.get("search"):
                parts_list.append(f"search={last_list_params.get('search')!r}")
            if last_list_params.get("status"):
                parts_list.append(f"status={last_list_params.get('status')}")
            if last_list_params.get("min_price_eth") is not None:
                parts_list.append(f"min_price_eth={last_list_params.get('min_price_eth')}")
            if last_list_params.get("max_price_eth") is not None:
                parts_list.append(f"max_price_eth={last_list_params.get('max_price_eth')}")
            state_str += f"\n**Last list_nfts query (for pagination — 'next N', 'next 5', 'more', 'next page'):** {', '.join(parts_list)}. To get the next N NFTs, use the same filters and sort with **skip={next_skip}** and **limit=N** (e.g. 'next 5' → skip={next_skip}, limit=5).\n"
        for k, v in session_state.items():
            if k in ("nft_list", "collection_list", "last_list_params"):
                continue
            state_str += f"- {k}: {v}\n"
        parts.append(state_str)
        
        # Add recent conversation history for context
        if history and len(history) > 0:
            history_str = "\n## Recent Conversation:\n"
            for msg in history[-10:]:  # Last 10 messages for continuity
                role = msg["role"].capitalize()
                content = msg["content"][:300]  # Truncate long messages
                history_str += f"**{role}**: {content}\n"
            parts.append(history_str)
        
        return "\n\n".join(parts)
