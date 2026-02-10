# HTML Pass-Through Fix

## Problem

The agent was receiving HTML components from tools but was **summarizing them into markdown tables** instead of passing them through verbatim to the user. This meant the frontend received only markdown text, not the styled HTML components.

### Root Cause

Large Language Models (LLMs) have a tendency to "be helpful" by summarizing tool outputs rather than passing them through as-is. The agent was:
1. Receiving HTML wrapped in `<!--HTML_COMPONENT::type-->...::END_HTML-->` markers from tools
2. Extracting the NFT data from the HTML
3. Creating its own markdown table/list
4. Discarding the original styled HTML

## Solution

Applied **triple-layered reinforcement** to force HTML pass-through:

### 1. Critical System Instructions (highest priority)

Added prominent warnings at the top of `nft_chatbot/agent/instructions.py`:

```
## ⚠️ CRITICAL RULE: HTML PASS-THROUGH (NEVER VIOLATE THIS) ⚠️

YOU MUST:
✅ Copy the ENTIRE HTML block (including markers) EXACTLY as-is
✅ You may add brief text before/after the HTML block

YOU MUST NEVER:
❌ Create your own tables, lists, or summaries of NFT data
❌ Remove or modify the HTML markers
❌ Summarize the HTML content into markdown
```

### 2. Tool-Level Instructions

Modified tool return statements in `nft_chatbot/tools/nft_tools.py` to include explicit instructions:

```python
return (
    f"Found {data['total']} NFTs matching the criteria.\n\n"
    f"IMPORTANT: Copy the entire HTML block below (including the markers) into your response:\n\n"
    f"{wrapped_html}\n\n"
    f"The HTML above is a complete, styled component. Do NOT create tables or summaries."
)
```

### 3. Examples of Correct vs. Wrong Responses

Provided explicit examples in the instructions:

**✅ CORRECT:**
```
Here are the top 10 NFTs:

<!--HTML_COMPONENT::grid-->
<!DOCTYPE html>...
::END_HTML-->

Let me know if you'd like details!
```

**❌ WRONG:**
```
Here are the top 10 NFTs:
| Rank | Name | Price |
|------|------|-------|
```

## Result

The agent now correctly passes through HTML components. The response structure is:

```json
{
  "blocks": [
    {
      "type": "text",
      "markdown": "Here are the top 5 NFTs:",
      "html": null,
      "template": null
    },
    {
      "type": "html_component",
      "markdown": null,
      "html": "<!DOCTYPE html>...",
      "template": "grid"
    }
  ]
}
```

## Testing

Verified with:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user", "message": "show me top 5 NFTs"}'
```

Response correctly contains:
- Text block with conversational context
- HTML component block with full styled HTML

## Key Learnings

1. **LLMs need explicit, repeated instructions** - Single mentions are not enough
2. **Show examples** - Demonstrate both correct and incorrect behavior
3. **Reinforce at multiple layers** - System prompt, tool responses, and response format
4. **Use visual markers** - Emojis (⚠️✅❌) help draw attention to critical rules
5. **Make consequences clear** - Explain WHY the HTML must be preserved (it's already styled and complete)
