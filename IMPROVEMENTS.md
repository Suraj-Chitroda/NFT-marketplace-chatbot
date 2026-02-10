# Improvements to Integrate from Old Version

Based on the original `agno-agent-old.py`, here are features to add to the new modular system:

## 1. Rate Limiting (HIGH PRIORITY)

**Old version:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/chat")
@limiter.limit("60/minute")
def chat(...):
```

**Add to new version:**
- Install: `pip install slowapi`
- Add to `nft_chatbot/main.py`

## 2. Response Headers (MEDIUM PRIORITY)

**Old version:**
```python
response.headers["X-User-Id-Used"] = user_id
response.headers["X-Session-Id-Used"] = session_id
```

**Add to new version:**
- Helpful for debugging and tracking
- Add to `nft_chatbot/main.py` chat endpoint

## 3. Header-based User/Session (OPTIONAL)

**Old version:**
```python
def get_user_id(x_user_id: Optional[str] = Header(None, alias="X-User-Id")) -> str:
    return x_user_id or str(uuid.uuid4())
```

**New version uses body params:**
```python
class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str]
```

**Decision:** Body params are better for most clients (easier to use). Headers are more RESTful but require custom header support.

## 4. Better Error Handling (HIGH PRIORITY)

**Old version:**
```python
if not GROQ_API_KEY:
    raise HTTPException(
        status_code=503,
        detail="GROQ_API_KEY is not set. Configure it and restart.",
    )
```

**Add to new version:**
- Check API key at startup
- Better error messages
- Add to `nft_chatbot/main.py` lifespan or startup event

## 5. Enhanced Tool Descriptions (MEDIUM PRIORITY)

**Old version has much better tool descriptions:**
```python
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
```

**Improve in:** `nft_chatbot/tools/nft_tools.py`

## 6. Logging Improvements (LOW PRIORITY)

**Old version:**
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nft-chatbot")
logger.info("Chat request user_id=%s session_id=%s", user_id, session_id)
```

**Add structured logging to new version.**

## 7. Better Agent Instructions (HIGH PRIORITY)

**Old version has clearer instructions:**
- Explicitly tells agent what NOT to do
- Explains when to use multiple tools
- Better context about referring to previous results

**Update:** `nft_chatbot/agent/instructions.py`

---

## Implementation Plan

### Phase 1: Critical Updates
1. ✅ Add rate limiting
2. ✅ Improve error handling (check API keys at startup)
3. ✅ Enhance agent instructions
4. ✅ Add response headers

### Phase 2: Nice-to-Have
1. Better logging
2. More detailed tool descriptions
3. Request timeout configuration

---

## Hybrid Approach Option

We could also create a **simplified version** that combines:
- Old version's simplicity (single file, Agno's native DB)
- New version's HTML template rendering

Would be useful for:
- Quick deployments
- Learning/demo purposes
- Low-complexity use cases

The full modular version is better for:
- Production systems
- Custom schema needs
- Multiple services
- Scaling
