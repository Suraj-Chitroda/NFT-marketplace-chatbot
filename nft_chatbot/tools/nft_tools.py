"""
Agno tools for NFT marketplace operations.
Uses existing backend template renderer.
Appends SESSION_DATA (for session state) so chat service can store last NFT list for context.
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

import httpx
from agno.tools import tool

SESSION_DATA_PATTERN = re.compile(r"\[SESSION_DATA\](.*?)\[/SESSION_DATA\]", re.DOTALL)


def _session_data_line(payload: dict) -> str:
    """Format session payload for appending to tool response. Stripped by chat service."""
    return f"\n[SESSION_DATA]{json.dumps(payload)}[/SESSION_DATA]"

# Import existing backend template agent
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from template_agent_enhanced import EnhancedTemplateAgent
from nft_chatbot.agent.response_parser import ResponseParser
from nft_chatbot.config import settings

# Initialize template agent
template_agent = EnhancedTemplateAgent()
NFT_API_BASE = settings.nft_api_base


@tool(
    name="list_nfts",
    description=(
        "Fetch a paginated list of NFTs from the marketplace with optional filtering, sorting, and display customization. "
        "\n\nUSE THIS TOOL WHEN the user asks to:"
        "\n- Browse or list NFTs (e.g., 'show me some NFTs', 'what NFTs are available?')"
        "\n- Filter by specific criteria (collection, blockchain, status, price range, rarity)"
        "\n- Sort results (by price, rarity, popularity, token ID)"
        "\n- Search for NFTs by name or description"
        "\n- Get the first page or next page of results"
        "\n\nSUPPORTS:"
        "\n- Filtering: collection, blockchain, status, price range (ETH), rarity range"
        "\n- Sorting: tokenId, price_eth, rarityRank, likes, views (asc or desc)"
        "\n- Pagination: limit (1-20 per request), skip (offset for next page — use for 'next N', 'more', 'next page')"
        "\n- View types: 'grid' (card view) or 'table' (list view)"
        "\n- Detail levels: 'minimal', 'standard', 'detailed', 'full'"
        "\n\nRETURNS: Styled HTML component with NFT data ready for display"
    ),
)
async def list_nfts(
    collection: Optional[str] = None,
    blockchain: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    min_price_eth: Optional[float] = None,
    max_price_eth: Optional[float] = None,
    min_rarity: Optional[int] = None,
    max_rarity: Optional[int] = None,
    sort_by: str = "tokenId",
    order: str = "asc",
    limit: int = 10,
    skip: int = 0,
    view_type: str = "grid",
    detail_level: str = "standard"
) -> str:
    """
    List NFTs from the marketplace with filtering, sorting, and pagination.
    
    Args:
        collection: Filter by collection name (e.g., "Meta Legends", "Digital Warriors")
        blockchain: Filter by blockchain (Ethereum, Polygon, Solana)
        status: Filter by status (listed, sold, auction, not_for_sale)
        search: Search in name, description, or collection
        min_price_eth: Minimum price in ETH
        max_price_eth: Maximum price in ETH
        min_rarity: Minimum rarity rank (lower is rarer)
        max_rarity: Maximum rarity rank (lower is rarer)
        sort_by: Sort field (tokenId, price_eth, rarityRank, likes, views)
        order: Sort order (asc, desc)
        limit: Number of NFTs to return (1-20)
        skip: Number of NFTs to skip (for "next N" / next page — use previous skip + previous limit)
        view_type: Display format - "grid" for card view, "table" for list view
        detail_level: Amount of info - "minimal", "standard", "detailed", or "full"
    
    Returns:
        Structured response with markdown context and HTML component
    """
    try:
        # Call NFT API - filter out None values to avoid validation errors
        params = {
            "limit": min(limit, 20),
            "skip": skip,
            "sort_by": sort_by,
            "order": order,
        }
        
        # Only add optional parameters if they have values
        if collection:
            params["collection"] = collection
        if blockchain:
            params["blockchain"] = blockchain
        if status:
            params["status"] = status
        if search:
            params["search"] = search
        if min_price_eth is not None:
            params["min_price_eth"] = min_price_eth
        if max_price_eth is not None:
            params["max_price_eth"] = max_price_eth
        if min_rarity is not None:
            params["min_rarity"] = min_rarity
        if max_rarity is not None:
            params["max_rarity"] = max_rarity
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{NFT_API_BASE}/nfts", params=params)
            response.raise_for_status()
            data = response.json()
        
        if not data.get("nfts"):
            return "No NFTs found matching your criteria. Try adjusting your filters."
        
        # Render HTML template using existing backend template agent
        template_name = "grid" if view_type == "grid" else "table"
        template_type = f"nft_{template_name}"
        html = template_agent.render_nft_list(
            nfts=data["nfts"],
            template_type=template_type,
            detail_level=detail_level
        )
        
        # Wrap HTML with markers for structured parsing
        wrapped_html = ResponseParser.wrap_html(html, template_name)
        
        # Build session data with full tool-received details for message history (agent context)
        nft_list = []
        for n in data.get("nfts", []) or []:
            if not n.get("id"):
                continue
            price = n.get("price") or {}
            last_sale = n.get("lastSale")
            owner = n.get("owner") or {}
            nft_list.append({
                "id": n.get("id"),
                "name": n.get("name"),
                "collection": n.get("collection", ""),
                "price_eth": price.get("eth"),
                "last_sale_eth": last_sale.get("eth") if isinstance(last_sale, dict) else None,
                "owner": owner.get("address") or owner.get("username") or "",
                "status": n.get("status", ""),
                "rarity_rank": n.get("rarityRank"),
            })
        # Store last list params so agent can do "next 5" with same filters/sort (skip = last skip + last limit)
        last_list_params = {
            "limit": limit,
            "skip": skip,
            "sort_by": sort_by,
            "order": order,
            "collection": collection,
            "blockchain": blockchain,
            "status": status,
            "search": search,
            "min_price_eth": min_price_eth,
            "max_price_eth": max_price_eth,
            "min_rarity": min_rarity,
            "max_rarity": max_rarity,
        }
        session_payload = {"nft_list": nft_list, "last_list_params": last_list_params}
        
        return (
            f"Found {data['total']} NFTs matching the criteria.\n\n"
            f"IMPORTANT: Copy the entire HTML block below (including the markers) into your response:\n\n"
            f"{wrapped_html}\n\n"
            f"The HTML above is a complete, styled component. Do NOT create tables or summaries."
            f"{_session_data_line(session_payload)}"
        )
    
    except httpx.HTTPError as e:
        return f"Error fetching NFTs from API: {str(e)}"
    except Exception as e:
        return f"Error rendering NFT list: {str(e)}"


@tool(
    name="list_collections",
    description=(
        "Fetch a paginated list of NFT collections from the marketplace with optional search, sorting, and display format. "
        "\n\nUSE THIS TOOL WHEN the user asks to:"
        "\n- Browse or list collections (e.g., 'show me collections', 'what collections are there?', 'list of collections')"
        "\n- Search for a collection by name"
        "\n- Sort collections by name, NFT count, or price range"
        "\n- See collections in grid (cards) or list/table format"
        "\n\nSUPPORTS:"
        "\n- Search: filter by collection name (substring match)"
        "\n- Sorting: name, nft_count, min_price_eth, max_price_eth (asc or desc)"
        "\n- Pagination: limit (1-20 per request), skip for next page"
        "\n- View types: 'grid' (card view) or 'table' (list view)"
        "\n\nRETURNS: Styled HTML component with collection data (name, NFT count, blockchains, price range)"
    ),
)
async def list_collections(
    search: Optional[str] = None,
    sort_by: str = "name",
    order: str = "asc",
    limit: int = 10,
    skip: int = 0,
    view_type: str = "grid",
) -> str:
    """
    List NFT collections with optional search, sorting, and pagination.

    Args:
        search: Search/filter by collection name (substring)
        sort_by: name, nft_count, min_price_eth, max_price_eth
        order: asc or desc
        limit: Number of collections to return (1-20)
        skip: Number to skip for pagination
        view_type: Display format - "grid" (cards) or "table" (list view)

    Returns:
        Structured response with markdown context and HTML component
    """
    try:
        params = {
            "limit": min(limit, 20),
            "skip": skip,
            "sort_by": sort_by,
            "order": order,
        }
        if search:
            params["search"] = search

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{NFT_API_BASE}/collections", params=params)
            response.raise_for_status()
            data = response.json()

        collections = data.get("collections") or []
        if not collections:
            return "No collections found matching your criteria. Try a different search or filters."

        template_type = "collection_grid" if view_type == "grid" else "collection_table"
        html = template_agent.render_collection_list(
            collections=collections,
            template_type=template_type,
            detail_level="standard",
        )
        wrapped_html = ResponseParser.wrap_html(html, template_type)

        collection_list = [
            {
                "name": c.get("name", ""),
                "nft_count": c.get("nft_count", 0),
                "blockchains": c.get("blockchains") or [],
            }
            for c in collections
        ]
        session_payload = {"collection_list": collection_list}

        return (
            f"Found **{len(collections)}** collection(s).\n\n"
            f"IMPORTANT: Copy the entire HTML block below (including the markers) into your response:\n\n"
            f"{wrapped_html}\n\n"
            f"The HTML above is a complete, styled component. Do NOT create tables or summaries."
            f"{_session_data_line(session_payload)}"
        )
    except httpx.HTTPError as e:
        return f"Error fetching collections from API: {str(e)}"
    except Exception as e:
        return f"Error rendering collection list: {str(e)}"


@tool(
    name="get_nft_details",
    description=(
        "Fetch complete details for a single NFT by its unique ID. "
        "\n\nUSE THIS TOOL WHEN the user asks about:"
        "\n- A specific NFT by ID (e.g., 'details of NFT nft-042', 'show me NFT #5', 'what is the price of NFT nft-001')"
        "\n- An NFT from a previous list (e.g., 'the first one', 'that NFT', 'the one you just showed')"
        "\n- More information about a particular NFT"
        "\n\nIMPORTANT:"
        "\n- You MUST call this tool with the exact nft_id; do NOT invent or guess IDs"
        "\n- If the user refers to an NFT from a previous list, use that NFT's actual id field"
        "\n- If you don't know the exact ID, ask the user or use list_nfts to find it first"
        "\n\nRETURNS: Styled HTML component with detailed NFT information including image, title, description, "
        "price, attributes, owner info, and transaction history"
    ),
)
async def get_nft_details(
    nft_id: str,
    detail_level: str = "detailed"
) -> str:
    """
    Get detailed information about a specific NFT.
    
    Args:
        nft_id: The NFT ID (e.g., "nft-001", "nft-042")
        detail_level: Amount of detail - "standard", "detailed", or "full"
    
    Returns:
        Structured response with markdown context and HTML component
    """
    try:
        # Call NFT API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{NFT_API_BASE}/nfts/{nft_id}")
            
            if response.status_code == 404:
                return f"NFT with ID '{nft_id}' was not found in our marketplace."
            
            response.raise_for_status()
            nft = response.json()
        
        # Render details template using existing backend template agent
        html = template_agent.render_nft_details(nft=nft, detail_level=detail_level)
        
        # Wrap HTML with markers for structured parsing
        wrapped_html = ResponseParser.wrap_html(html, "details")
        
        # Full detail data for message history (agent context)
        price = nft.get("price") or {}
        last_sale = nft.get("lastSale")
        owner = nft.get("owner") or {}
        attrs = nft.get("attributes") or []
        detail_summary = {
            "id": nft.get("id"),
            "name": nft.get("name"),
            "collection": nft.get("collection", ""),
            "description": (nft.get("description") or "")[:300],
            "price_eth": price.get("eth"),
            "last_sale_eth": last_sale.get("eth") if isinstance(last_sale, dict) else None,
            "owner": owner.get("address") or owner.get("username") or "",
            "status": nft.get("status", ""),
            "rarity_rank": nft.get("rarityRank"),
            "blockchain": nft.get("blockchain", ""),
            "attributes": [f"{a.get('trait_type', '')}: {a.get('value', '')}" for a in attrs[:10]],
        }
        session_payload = {"last_detail_id": nft.get("id"), "detail_summary": detail_summary}
        
        return (
            f"Retrieved details for **{nft['name']}**.\n\n"
            f"IMPORTANT: Copy the entire HTML block below (including the markers) into your response:\n\n"
            f"{wrapped_html}\n\n"
            f"The HTML above is a complete, styled component. Do NOT create tables or summaries."
            f"{_session_data_line(session_payload)}"
        )
    
    except httpx.HTTPError as e:
        return f"Error fetching NFT details from API: {str(e)}"
    except Exception as e:
        return f"Error rendering NFT details: {str(e)}"
