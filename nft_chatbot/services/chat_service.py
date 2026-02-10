"""
Chat service - orchestrates the full chat flow.
Keeps main.py thin and focused on HTTP handling.
Extracts SESSION_DATA from tool outputs to update session state (last NFT list, etc.).
"""

import json
import re
from typing import List, Optional, Tuple

from nft_chatbot.db.repository import ChatRepository
from nft_chatbot.agent.context_manager import ContextManager
from nft_chatbot.agent.response_parser import ResponseParser, HTML_START, HTML_END
from nft_chatbot.agent.nft_agent import run_agent_with_context
from nft_chatbot.agent.instructions import BASE_INSTRUCTIONS
from nft_chatbot.models.chat import ContentBlock
from nft_chatbot.models.memory_keys import (
    MEMORY_TYPE_PERSONAL,
    MEMORY_TYPE_PREFERENCE,
    MEMORY_TYPE_INTENT,
    KEY_DISPLAY_NAME,
    KEY_TIMEZONE,
    KEY_LANGUAGE,
    KEY_PREFERRED_VIEW,
    KEY_DETAIL_LEVEL,
    KEY_RESPONSE_FORMAT,
    KEY_STYLE_PREFERENCE,
    KEY_PRIMARY_INTENT,
    KEY_INTEREST_COLLECTIONS,
    KEY_PRICE_RANGE_INTEREST,
)

# Non-greedy for extraction (each payload)
SESSION_DATA_PATTERN = re.compile(r"\[SESSION_DATA\](.*?)\[/SESSION_DATA\]", re.DOTALL | re.IGNORECASE)
# Strip: with closing tag (repeat to handle nested/literal in JSON), then orphan (no closing tag) to end of string
SESSION_DATA_STRIP_PATTERN = re.compile(r"\[SESSION_DATA\].*?\[/SESSION_DATA\]", re.DOTALL | re.IGNORECASE)
SESSION_DATA_ORPHAN_STRIP_PATTERN = re.compile(r"\[SESSION_DATA\].*$", re.DOTALL | re.IGNORECASE)
STORE_PERSONAL_PATTERN = re.compile(r"\[STORE_PERSONAL\](.*?)\[/STORE_PERSONAL\]", re.DOTALL)
STORE_PERSONAL_STRIP_PATTERN = re.compile(r"\[STORE_PERSONAL\].*?\[/STORE_PERSONAL\]", re.DOTALL | re.IGNORECASE)
STORE_PREFERENCE_PATTERN = re.compile(r"\[STORE_PREFERENCE\](.*?)\[/STORE_PREFERENCE\]", re.DOTALL)
STORE_PREFERENCE_STRIP_PATTERN = re.compile(r"\[STORE_PREFERENCE\].*?\[/STORE_PREFERENCE\]", re.DOTALL | re.IGNORECASE)

# User asks not to store / forget personal details
DONT_REMEMBER_PERSONAL = re.compile(
    r"\b(don't remember|do not remember|forget|don't store|do not store|remove|delete)\s+(my\s+)?(name|details?|personal|info|information)\b",
    re.I
)
# User explicitly asks to remember something (preferences/intents stored only then)
# Match: remember/save/store/keep/share + (optional that/my/this) + preference/choice/prefer/like, or "sharing my preference", "this is my preference"
REMEMBER_ASK_PATTERN = re.compile(
    r"\b(remember|save|store|keep|share|sharing)\s+(that\s+)?(my\s+)?(this\s+)?(preference|preferences|choice|choices|that\s+i\s+prefer|that\s+i\s+like|i\s+prefer|i\s+like)\b"
    r"|\b(this\s+is|that'?s?)\s+(my\s+)?(preference|choice)\b"
    r"|\b(want\s+to|would\s+like\s+to|please)\s+(remember|save|store|keep)\s+(my\s+)?(preference|choice|that\s+i\s+prefer)?\b",
    re.I
)

NAME_PATTERNS = [
    re.compile(r"(?:call me|my name is|i'?m|i am|this is)\s+([a-zA-Z][a-zA-Z0-9_\s]{0,50})", re.I),
    re.compile(r"(?:you can call me|call me)\s+([a-zA-Z][a-zA-Z0-9_\s]{0,50})", re.I),
]
COLLECTION_INTEREST_PATTERN = re.compile(r"(?:interested in|like|love|collect)\s+(?:the\s+)?(?:collections?\s+)?([a-zA-Z0-9\s,]+?)(?:\s+collection)?[\.\!,\s]*$", re.I)
PRICE_RANGE_PATTERN = re.compile(r"(?:under|below|max|within)\s+(\d+(?:\.\d+)?)\s*ETH", re.I)


def _extract_and_strip_session_data(raw: str) -> Tuple[dict, str]:
    """Extract all SESSION_DATA payloads from agent response and strip them. Returns (merged_state_update, stripped_content)."""
    updates = {}
    for m in SESSION_DATA_PATTERN.finditer(raw):
        try:
            payload = json.loads(m.group(1).strip())
            if isinstance(payload, dict):
                updates.update(payload)
        except (json.JSONDecodeError, TypeError):
            continue
    # Strip all [SESSION_DATA]...[/SESSION_DATA] blocks (repeat until none left)
    stripped = raw
    while SESSION_DATA_STRIP_PATTERN.search(stripped):
        stripped = SESSION_DATA_STRIP_PATTERN.sub("", stripped)
    # Strip orphan [SESSION_DATA]... with no closing tag (to end of string)
    stripped = SESSION_DATA_ORPHAN_STRIP_PATTERN.sub("", stripped)
    stripped = stripped.strip()
    return updates, stripped


def _extract_and_strip_store_personal(raw: str) -> Tuple[dict, str]:
    """Extract [STORE_PERSONAL] from LLM response and strip. Returns (personal_dict, stripped_content)."""
    personal = {}
    for m in STORE_PERSONAL_PATTERN.finditer(raw):
        try:
            payload = json.loads(m.group(1).strip())
            if isinstance(payload, dict):
                personal.update(payload)
        except (json.JSONDecodeError, TypeError):
            continue
    stripped = STORE_PERSONAL_STRIP_PATTERN.sub("", raw).strip()
    return personal, stripped


def _extract_and_strip_store_preference(raw: str) -> Tuple[dict, str]:
    """Extract [STORE_PREFERENCE] from LLM response and strip. Returns (preference_dict, stripped_content)."""
    prefs = {}
    for m in STORE_PREFERENCE_PATTERN.finditer(raw):
        try:
            payload = json.loads(m.group(1).strip())
            if isinstance(payload, dict):
                prefs.update(payload)
        except (json.JSONDecodeError, TypeError):
            continue
    stripped = STORE_PREFERENCE_STRIP_PATTERN.sub("", raw).strip()
    return prefs, stripped


def _sanitize_response_for_user(text: str) -> str:
    """
    Remove any remaining internal markers and stray lines so the user never sees
    [SESSION_DATA], [STORE_*], or raw JSON. Response to the user must be only markdown and HTML.
    """
    if not text or not text.strip():
        return text
    # Remove internal marker blocks (with closing tag)
    for pattern in [
        re.compile(r"\[SESSION_DATA\].*?\[/SESSION_DATA\]", re.DOTALL | re.IGNORECASE),
        re.compile(r"\[STORE_PERSONAL\].*?\[/STORE_PERSONAL\]", re.DOTALL | re.IGNORECASE),
        re.compile(r"\[STORE_PREFERENCE\].*?\[/STORE_PREFERENCE\]", re.DOTALL | re.IGNORECASE),
    ]:
        while pattern.search(text):
            text = pattern.sub("", text)
    # Remove orphan [SESSION_DATA] or [STORE_*] with no closing tag (to end of string)
    for pattern in [
        re.compile(r"\[SESSION_DATA\].*$", re.DOTALL | re.IGNORECASE),
        re.compile(r"\[STORE_PERSONAL\].*$", re.DOTALL | re.IGNORECASE),
        re.compile(r"\[STORE_PREFERENCE\].*$", re.DOTALL | re.IGNORECASE),
    ]:
        text = pattern.sub("", text)
    # Remove standalone lines that are only opening/closing tags
    lines = text.split("\n")
    out = []
    for line in lines:
        s = line.strip()
        if re.match(r"^\[/?SESSION_DATA\]$", s, re.I) or re.match(r"^\[/?STORE_PERSONAL\]$", s, re.I) or re.match(r"^\[/?STORE_PREFERENCE\]$", s, re.I):
            continue
        out.append(line)
    text = "\n".join(out).strip()
    return text


# Pattern for HTML component blocks (same as response_parser) for replacing with compact summary in stored history
_HTML_BLOCK_PATTERN = re.compile(
    rf"{re.escape(HTML_START)}(\w+)-->(.*?){re.escape(HTML_END)}",
    re.DOTALL,
)
# Orphaned HTML block (no closing ::END_HTML::) - replace so we never store raw HTML
_ORPHAN_HTML_PATTERN = re.compile(
    rf"{re.escape(HTML_START)}\w+-->.*",
    re.DOTALL,
)


def _build_content_for_storage(stripped_response: str, state_updates: dict) -> str:
    """
    Replace full HTML blocks with compact text of the tool-received data
    so stored history has full context (id, name, price, etc.) without raw HTML.
    """
    nft_list = state_updates.get("nft_list") or []
    collection_list = state_updates.get("collection_list") or []
    detail_summary = state_updates.get("detail_summary") or {}
    last_detail_id = state_updates.get("last_detail_id") or ""

    def _nft_line(n: dict) -> str:
        price = n.get("price_eth")
        p = f" {price} ETH" if price is not None else ""
        last = n.get("last_sale_eth")
        ls = f" last_sale={last} ETH" if last is not None else ""
        owner = (n.get("owner") or "")[:16]
        owner = f" owner={owner}..." if owner else ""
        return (
            f"{n.get('id', '')} {n.get('name', '')} ({n.get('collection', '')})"
            f"{p}{ls}{owner} status={n.get('status', '')} rarity_rank={n.get('rarity_rank', '')}"
        )

    def _detail_block(d: dict) -> str:
        if not d:
            return f"[Shown: details for {last_detail_id}]" if last_detail_id else "[Shown: NFT details]"
        lines = [
            f"id={d.get('id')} name={d.get('name')} collection={d.get('collection')}",
            f"price_eth={d.get('price_eth')} last_sale_eth={d.get('last_sale_eth')} status={d.get('status')}",
            f"owner={d.get('owner', '')} blockchain={d.get('blockchain', '')} rarity_rank={d.get('rarity_rank')}",
            f"description: {d.get('description', '')}",
        ]
        attrs = d.get("attributes") or []
        if attrs:
            lines.append("attributes: " + ", ".join(attrs))
        return "[Shown NFT details: " + " | ".join(lines) + "]"

    def _collection_line(c: dict) -> str:
        return f"{c.get('name', '')} ({c.get('nft_count', 0)} NFTs)"

    def replacer(match):
        template_type = match.group(1).lower()
        if template_type in ("grid", "table"):
            if nft_list:
                parts = [_nft_line(n) for n in nft_list[:20]]
                summary = "; ".join(parts)
                if len(nft_list) > 20:
                    summary += f" ... and {len(nft_list) - 20} more"
                return f"[Shown {len(nft_list)} NFTs ({template_type}): {summary}]"
            return f"[Shown: NFT list ({template_type})]"
        if template_type in ("collection_grid", "collection_table"):
            if collection_list:
                parts = [_collection_line(c) for c in collection_list[:20]]
                summary = "; ".join(parts)
                if len(collection_list) > 20:
                    summary += f" ... and {len(collection_list) - 20} more"
                return f"[Shown {len(collection_list)} collections ({template_type}): {summary}]"
            return f"[Shown: collection list ({template_type})]"
        if template_type == "details":
            return _detail_block(detail_summary)
        return f"[Shown: {template_type} component]"

    out = _HTML_BLOCK_PATTERN.sub(replacer, stripped_response)
    # Remove any orphaned HTML (unclosed block) so we never persist raw HTML
    out = _ORPHAN_HTML_PATTERN.sub("[Shown: component - content omitted]", out)
    return out


def _build_blocks_json_for_storage(
    blocks: List[ContentBlock], state_updates: dict
) -> str:
    """
    Build storage as JSON array of blocks: [{markdown: "", html_tools_data: ""}, ...].
    No HTML stored; only markdown and tool-derived data for each block.
    """
    nft_list = state_updates.get("nft_list") or []
    collection_list = state_updates.get("collection_list") or []
    detail_summary = state_updates.get("detail_summary") or {}
    last_detail_id = state_updates.get("last_detail_id") or ""

    def _nft_list_summary() -> str:
        if not nft_list:
            return ""
        parts = [
            f"{n.get('id', '')} {n.get('name', '')} ({n.get('collection', '')}) "
            f"price_eth={n.get('price_eth')} last_sale_eth={n.get('last_sale_eth')} "
            f"owner={str(n.get('owner') or '')[:16]} status={n.get('status')} rarity_rank={n.get('rarity_rank')}"
            for n in nft_list[:20]
        ]
        line = "; ".join(parts)
        if len(nft_list) > 20:
            line += f" ... and {len(nft_list) - 20} more"
        return line

    def _detail_summary_text() -> str:
        if not detail_summary:
            return f"[details for {last_detail_id}]" if last_detail_id else ""
        d = detail_summary
        lines = [
            f"id={d.get('id')} name={d.get('name')} collection={d.get('collection')}",
            f"price_eth={d.get('price_eth')} last_sale_eth={d.get('last_sale_eth')} status={d.get('status')}",
            f"owner={d.get('owner', '')} blockchain={d.get('blockchain', '')} rarity_rank={d.get('rarity_rank')}",
            f"description: {(d.get('description') or '')[:200]}",
        ]
        attrs = d.get("attributes") or []
        if attrs:
            lines.append("attributes: " + ", ".join(attrs))
        return " | ".join(lines)

    def _collection_list_summary() -> str:
        if not collection_list:
            return ""
        parts = [f"{c.get('name', '')} nft_count={c.get('nft_count', 0)}" for c in collection_list[:20]]
        line = "; ".join(parts)
        if len(collection_list) > 20:
            line += f" ... and {len(collection_list) - 20} more"
        return line

    nft_used = 0
    collection_used = 0
    detail_used = 0
    out_blocks: List[dict] = []

    for b in blocks:
        if b.type == "text":
            out_blocks.append({
                "markdown": (b.markdown or "").strip(),
                "html_tools_data": "",
            })
        elif b.type == "html_component" and b.template:
            t = b.template.lower()
            if t in ("grid", "table"):
                html_tools_data = _nft_list_summary() if not nft_used else ""
                nft_used = 1
            elif t in ("collection_grid", "collection_table"):
                html_tools_data = _collection_list_summary() if not collection_used else ""
                collection_used = 1
            elif t == "details":
                html_tools_data = _detail_summary_text() if not detail_used else ""
                detail_used = 1
            else:
                html_tools_data = ""
            out_blocks.append({"markdown": "", "html_tools_data": html_tools_data})
        else:
            out_blocks.append({"markdown": (b.markdown or "").strip(), "html_tools_data": ""})

    return json.dumps(out_blocks)


class ChatService:
    """Orchestrates agent, DB, and response parsing."""
    
    def __init__(self, repository: ChatRepository):
        self.repo = repository
        self.context_mgr = ContextManager(repository)
        self.response_parser = ResponseParser()
    
    async def process_message(
        self,
        user_id: str,
        session_id: Optional[str],
        message: str
    ) -> tuple[str, List[ContentBlock]]:
        """
        Process a chat message end-to-end.
        
        Args:
            user_id: External user identifier
            session_id: Optional session ID for continuity
            message: User's message
        
        Returns:
            (session_id, content_blocks)
        """
        # 1. Get or create user
        user = await self.repo.get_or_create_user(user_id)
        
        # 2. Get or create session
        if session_id:
            session = await self.repo.get_session(session_id)
            if not session:
                session = await self.repo.create_session(user.id)
        else:
            session = await self.repo.create_session(user.id)
        
        # 3. Save user message
        await self.repo.add_message(
            session_id=session.id,
            role="user",
            content=message
        )
        
        # 4. Build context (enough history for "the one you showed" and continuity)
        context = await self.context_mgr.build_context(
            user_id=user.id,
            session_id=session.id,
            max_history=20
        )
        
        # 5. Build system prompt with history context
        system_prompt = self.context_mgr.build_system_prompt(
            base_instructions=BASE_INSTRUCTIONS,
            memories=context["memories"],
            session_state=context["session_state"],
            history=context["history"]
        )
        
        # 6. Run agent
        raw_response = await run_agent_with_context(
            message=message,
            system_prompt=system_prompt
        )

        # 7. Extract SESSION_DATA from tool output (last NFT list, etc.) and strip from response
        state_updates, stripped_response = _extract_and_strip_session_data(raw_response)
        if state_updates:
            await self.repo.update_session_state(session.id, state_updates)

        # 8. Extract personal details from LLM [STORE_PERSONAL] and strip from response
        personal_from_llm, stripped_response = _extract_and_strip_store_personal(stripped_response)
        # 8b. Extract preferences from LLM [STORE_PREFERENCE] and strip from response
        preference_from_llm, stripped_response = _extract_and_strip_store_preference(stripped_response)

        # 8c. Final sanitization: remove any remaining internal markers so response is only markdown/HTML
        stripped_response = _sanitize_response_for_user(stripped_response)

        # 9. Parse to structured blocks (use stripped response so user never sees SESSION_DATA / STORE_*)
        blocks = self.response_parser.parse(stripped_response)

        # 9b. Sanitize each block's markdown so no internal data is ever sent to the user; drop blocks that become empty
        sanitized_blocks = []
        for b in blocks:
            if b.type == "text" and (b.markdown or "").strip():
                cleaned = _sanitize_response_for_user(b.markdown or "").strip()
                if cleaned:
                    sanitized_blocks.append(ContentBlock(
                        type=b.type,
                        markdown=cleaned,
                        html=b.html,
                        template=b.template,
                    ))
            else:
                sanitized_blocks.append(b)

        # 10. Save assistant response as array of blocks [{markdown, html_tools_data}, ...]; no HTML stored
        storage_json = _build_blocks_json_for_storage(blocks, state_updates)
        await self.repo.add_message(
            session_id=session.id,
            role="assistant",
            content=storage_json,
            content_type="blocks_json"
        )

        # 11. Update user memory: personal only when user did not ask to forget; preferences/intents only when user asked to remember (or LLM sent [STORE_PREFERENCE])
        await self._extract_and_store_memory(user.id, message, personal_from_llm, preference_from_llm)

        return session.id, sanitized_blocks
    
    async def _extract_and_store_memory(
        self,
        user_id: str,
        message: str,
        personal_from_llm: Optional[dict] = None,
        preference_from_llm: Optional[dict] = None,
    ) -> None:
        """
        Store in user memory only when appropriate:
        - Personal details: from user message and/or LLM [STORE_PERSONAL]; do not store if user asked not to remember.
        - Preferences and intents: when user explicitly asks to remember (e.g. "remember my preference") or when LLM sends [STORE_PREFERENCE].
        """
        msg = message.strip()
        msg_lower = msg.lower()
        personal_from_llm = personal_from_llm or {}
        preference_from_llm = preference_from_llm or {}

        if DONT_REMEMBER_PERSONAL.search(msg):
            await self.repo.delete_memories_by_type(user_id, MEMORY_TYPE_PERSONAL)
            return

        # --- Personal details: store from message regex and from LLM output ---
        for pat in NAME_PATTERNS:
            m = pat.search(msg)
            if m:
                name = m.group(1).strip()
                if len(name) <= 50 and name.lower() not in ("me", "i", "a", "the"):
                    await self.repo.upsert_memory(user_id, MEMORY_TYPE_PERSONAL, KEY_DISPLAY_NAME, name)
                break
        if personal_from_llm.get(KEY_DISPLAY_NAME):
            await self.repo.upsert_memory(
                user_id, MEMORY_TYPE_PERSONAL, KEY_DISPLAY_NAME,
                str(personal_from_llm[KEY_DISPLAY_NAME])[:100]
            )
        if personal_from_llm.get(KEY_TIMEZONE):
            await self.repo.upsert_memory(
                user_id, MEMORY_TYPE_PERSONAL, KEY_TIMEZONE,
                str(personal_from_llm[KEY_TIMEZONE])[:100]
            )
        if personal_from_llm.get(KEY_LANGUAGE):
            await self.repo.upsert_memory(
                user_id, MEMORY_TYPE_PERSONAL, KEY_LANGUAGE,
                str(personal_from_llm[KEY_LANGUAGE])[:50]
            )

        # --- Preferences and intents: store when user asks to remember OR LLM sent [STORE_PREFERENCE] ---
        user_asked_remember = REMEMBER_ASK_PATTERN.search(msg)
        if not user_asked_remember and not preference_from_llm:
            return

        # Prefer LLM-provided preference values when present; else infer from message
        pref_view = preference_from_llm.get(KEY_PREFERRED_VIEW) or preference_from_llm.get("preferred_view")
        if pref_view and str(pref_view).lower() in ("grid", "table"):
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_PREFERENCE, KEY_PREFERRED_VIEW, str(pref_view).lower())
        elif "table" in msg_lower or "list view" in msg_lower or "list format" in msg_lower or ("list" in msg_lower and ("view" in msg_lower or "prefer" in msg_lower or "preference" in msg_lower)):
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_PREFERENCE, KEY_PREFERRED_VIEW, "table")
        elif "grid" in msg_lower or "card view" in msg_lower or "grid format" in msg_lower:
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_PREFERENCE, KEY_PREFERRED_VIEW, "grid")
        detail_level = preference_from_llm.get(KEY_DETAIL_LEVEL) or preference_from_llm.get("detail_level")
        if detail_level and str(detail_level).lower() in ("minimal", "standard", "detailed", "full"):
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_PREFERENCE, KEY_DETAIL_LEVEL, str(detail_level).lower())
        elif "more detail" in msg_lower or "full info" in msg_lower or "detailed" in msg_lower:
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_PREFERENCE, KEY_DETAIL_LEVEL, "detailed")
        elif "brief" in msg_lower or "quick" in msg_lower or "minimal" in msg_lower or "less detail" in msg_lower:
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_PREFERENCE, KEY_DETAIL_LEVEL, "minimal")
        elif "standard" in msg_lower and ("detail" in msg_lower or "info" in msg_lower):
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_PREFERENCE, KEY_DETAIL_LEVEL, "standard")
        response_fmt = preference_from_llm.get(KEY_RESPONSE_FORMAT) or preference_from_llm.get("response_format")
        if response_fmt and str(response_fmt).lower() in ("concise", "balanced", "detailed"):
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_PREFERENCE, KEY_RESPONSE_FORMAT, str(response_fmt).lower())
        elif "short" in msg_lower or "concise" in msg_lower or "quick answer" in msg_lower:
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_PREFERENCE, KEY_RESPONSE_FORMAT, "concise")
        elif "detailed" in msg_lower or "full" in msg_lower or "explain more" in msg_lower:
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_PREFERENCE, KEY_RESPONSE_FORMAT, "detailed")
        elif "balanced" in msg_lower:
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_PREFERENCE, KEY_RESPONSE_FORMAT, "balanced")
        if "minimal" in msg_lower and ("style" in msg_lower or "look" in msg_lower or "prefer" in msg_lower):
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_PREFERENCE, KEY_STYLE_PREFERENCE, "minimal")
        elif "rich" in msg_lower or "more style" in msg_lower:
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_PREFERENCE, KEY_STYLE_PREFERENCE, "rich")
        if "just browsing" in msg_lower or "browsing" in msg_lower or "looking around" in msg_lower:
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_INTENT, KEY_PRIMARY_INTENT, "browsing")
        elif "looking to buy" in msg_lower or "want to buy" in msg_lower or "buying" in msg_lower:
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_INTENT, KEY_PRIMARY_INTENT, "buying")
        elif "collector" in msg_lower or "collecting" in msg_lower:
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_INTENT, KEY_PRIMARY_INTENT, "collecting")
        elif "research" in msg_lower or "comparing" in msg_lower or "analysis" in msg_lower:
            await self.repo.upsert_memory(user_id, MEMORY_TYPE_INTENT, KEY_PRIMARY_INTENT, "research")
        coll_m = COLLECTION_INTEREST_PATTERN.search(msg)
        if coll_m:
            raw = coll_m.group(1).strip()
            if len(raw) <= 200:
                await self.repo.upsert_memory(user_id, MEMORY_TYPE_INTENT, KEY_INTEREST_COLLECTIONS, raw)
        price_m = PRICE_RANGE_PATTERN.search(msg)
        if price_m:
            await self.repo.upsert_memory(
                user_id, MEMORY_TYPE_INTENT, KEY_PRICE_RANGE_INTEREST,
                f"under {price_m.group(1)} ETH"
            )
