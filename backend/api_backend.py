"""
NFT API Backend using data2.json as database.

Features:
- GET /nfts - List NFTs with filtering, sorting, and pagination
- GET /nfts/{id} - Get single NFT by ID
- GET /collections - List NFT collections with search, sorting, and pagination
- Supports filtering by collection, blockchain, status, price range
- Supports sorting by price, rarity, likes, views, mintDate (NFTs); name, nft_count, min/max_price_eth (collections)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import dotenv
dotenv.load_dotenv()

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("nft-api-backend")

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------

app = FastAPI(
    title="NFT API Backend",
    version="1.0.0",
    description="NFT API backend using data2.json with filtering, sorting, and pagination.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------

DATA_FILE = os.getenv("NFT_DATA_FILE", "data2.json")


def load_data() -> list[dict[str, Any]]:
    """Load NFT data from JSON file."""
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Data file {DATA_FILE} not found")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {DATA_FILE}: {e}")
        return []


# -----------------------------------------------------------------------------
# Response models
# -----------------------------------------------------------------------------


class Creator(BaseModel):
    """Creator information."""
    address: str
    username: str
    verified: bool


class Owner(BaseModel):
    """Owner information."""
    address: str
    username: str


class Price(BaseModel):
    """Price information."""
    eth: float
    usd: int


class LastSale(BaseModel):
    """Last sale information."""
    eth: float
    date: str


class Attribute(BaseModel):
    """NFT attribute."""
    trait_type: str
    value: str
    rarity: str


class Stats(BaseModel):
    """NFT stats."""
    power: int
    speed: int
    intelligence: int


class HistoryEvent(BaseModel):
    """History event."""
    event: str
    from_: str = Field(..., alias="from")
    to: str
    date: str


class NFTResponse(BaseModel):
    """Single NFT response model."""
    id: str
    tokenId: int
    name: str
    collection: str
    description: str
    image: str
    thumbnail: str
    creator: Creator
    owner: Owner
    blockchain: str
    contractAddress: str
    mintDate: str
    price: Price
    lastSale: Optional[LastSale] = None
    likes: int
    views: int
    status: str
    rarityRank: int
    attributes: list[Attribute]
    stats: Stats
    utility: list[str]
    history: list[HistoryEvent]

    model_config = {"populate_by_name": True}


class NFTsListResponse(BaseModel):
    """List response model with pagination info."""
    nfts: list[NFTResponse]
    total: int
    limit: int
    skip: int


class CollectionResponse(BaseModel):
    """Single collection summary (derived from NFT data)."""
    name: str
    nft_count: int
    blockchains: list[str]
    min_price_eth: Optional[float] = None
    max_price_eth: Optional[float] = None


class CollectionsListResponse(BaseModel):
    """List of collections with pagination."""
    collections: list[CollectionResponse]
    total: int
    limit: int
    skip: int


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------


def filter_nfts(
    nfts: list[dict[str, Any]],
    collection: Optional[str] = None,
    blockchain: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    min_price_eth: Optional[float] = None,
    max_price_eth: Optional[float] = None,
    min_price_usd: Optional[float] = None,
    max_price_usd: Optional[float] = None,
    min_rarity: Optional[int] = None,
    max_rarity: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Filter NFTs based on criteria."""
    filtered = nfts

    if collection:
        filtered = [
            nft for nft in filtered
            if nft.get("collection", "").lower() == collection.lower()
        ]

    if blockchain:
        filtered = [
            nft for nft in filtered
            if nft.get("blockchain", "").lower() == blockchain.lower()
        ]

    if status:
        filtered = [
            nft for nft in filtered
            if nft.get("status", "").lower() == status.lower()
        ]

    if search:
        search_lower = search.lower()
        filtered = [
            nft for nft in filtered
            if search_lower in nft.get("name", "").lower()
            or search_lower in nft.get("description", "").lower()
            or search_lower in nft.get("collection", "").lower()
        ]

    if min_price_eth is not None:
        filtered = [
            nft for nft in filtered
            if nft.get("price", {}).get("eth", 0) >= min_price_eth
        ]

    if max_price_eth is not None:
        filtered = [
            nft for nft in filtered
            if nft.get("price", {}).get("eth", 0) <= max_price_eth
        ]

    if min_price_usd is not None:
        filtered = [
            nft for nft in filtered
            if nft.get("price", {}).get("usd", 0) >= min_price_usd
        ]

    if max_price_usd is not None:
        filtered = [
            nft for nft in filtered
            if nft.get("price", {}).get("usd", 0) <= max_price_usd
        ]

    if min_rarity is not None:
        filtered = [
            nft for nft in filtered
            if nft.get("rarityRank", 1000) >= min_rarity
        ]

    if max_rarity is not None:
        filtered = [
            nft for nft in filtered
            if nft.get("rarityRank", 1000) <= max_rarity
        ]

    return filtered


def sort_nfts(
    nfts: list[dict[str, Any]],
    sort_by: str = "tokenId",
    order: str = "asc",
) -> list[dict[str, Any]]:
    """Sort NFTs by field."""
    valid_sort_fields = [
        "tokenId", "name", "collection", "mintDate",
        "price_eth", "price_usd", "rarityRank", "likes", "views"
    ]

    if sort_by not in valid_sort_fields:
        sort_by = "tokenId"

    reverse = order.lower() == "desc"

    def get_sort_key(nft: dict[str, Any]) -> Any:
        if sort_by == "price_eth":
            return nft.get("price", {}).get("eth", 0)
        elif sort_by == "price_usd":
            return nft.get("price", {}).get("usd", 0)
        elif sort_by == "tokenId":
            return nft.get("tokenId", 0)
        elif sort_by == "rarityRank":
            return nft.get("rarityRank", 1000)
        elif sort_by == "likes":
            return nft.get("likes", 0)
        elif sort_by == "views":
            return nft.get("views", 0)
        elif sort_by == "mintDate":
            return nft.get("mintDate", "")
        else:
            return str(nft.get(sort_by, "")).lower()

    return sorted(nfts, key=get_sort_key, reverse=reverse)


def build_collections_from_nfts(
    nfts: list[dict[str, Any]],
    search: Optional[str] = None,
    sort_by: str = "name",
    order: str = "asc",
    limit: int = 20,
    skip: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """
    Build unique collections from NFT data with optional search, sort, and pagination.
    Returns (list of collection dicts, total count).
    """
    # Group by collection name and aggregate
    by_name: dict[str, dict[str, Any]] = {}
    for nft in nfts:
        name = (nft.get("collection") or "").strip()
        if not name:
            continue
        if name not in by_name:
            prices = []
            blockchains = set()
            for x in nfts:
                if (x.get("collection") or "").strip() == name:
                    p = x.get("price") or {}
                    eth = p.get("eth")
                    if eth is not None:
                        prices.append(float(eth))
                    bc = x.get("blockchain")
                    if bc:
                        blockchains.add(str(bc))
            by_name[name] = {
                "name": name,
                "nft_count": sum(1 for x in nfts if (x.get("collection") or "").strip() == name),
                "blockchains": sorted(blockchains),
                "min_price_eth": min(prices) if prices else None,
                "max_price_eth": max(prices) if prices else None,
            }
    collections = list(by_name.values())

    if search:
        search_lower = search.lower()
        collections = [c for c in collections if search_lower in (c.get("name") or "").lower()]

    valid_sort = ("name", "nft_count", "min_price_eth", "max_price_eth")
    if sort_by not in valid_sort:
        sort_by = "name"
    reverse = order.lower() == "desc"

    def key(c: dict[str, Any]) -> Any:
        if sort_by == "name":
            return (c.get("name") or "").lower()
        if sort_by == "nft_count":
            return c.get("nft_count", 0)
        if sort_by == "min_price_eth":
            v = c.get("min_price_eth")
            return (v is not None, v if v is not None else 0)
        if sort_by == "max_price_eth":
            v = c.get("max_price_eth")
            return (v is not None, v if v is not None else 0)
        return c.get("name", "")

    collections = sorted(collections, key=key, reverse=reverse)
    total = len(collections)
    paginated = collections[skip : skip + limit]
    return paginated, total


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------


@app.get("/nfts", response_model=NFTsListResponse)
def get_nfts(
    limit: int = Query(default=20, ge=1, le=100, description="Number of NFTs per page"),
    skip: int = Query(default=0, ge=0, description="Number of NFTs to skip (pagination)"),
    sort_by: str = Query(
        default="tokenId",
        description="Field to sort by: tokenId, name, collection, mintDate, price_eth, price_usd, rarityRank, likes, views",
    ),
    order: str = Query(default="asc", description="Sort order: asc or desc"),
    collection: Optional[str] = Query(default=None, description="Filter by collection name"),
    blockchain: Optional[str] = Query(default=None, description="Filter by blockchain"),
    status: Optional[str] = Query(default=None, description="Filter by status (listed, sold, auction, not_for_sale)"),
    search: Optional[str] = Query(default=None, description="Search in name, description, or collection"),
    min_price_eth: Optional[float] = Query(default=None, ge=0, description="Minimum price in ETH"),
    max_price_eth: Optional[float] = Query(default=None, ge=0, description="Maximum price in ETH"),
    min_price_usd: Optional[float] = Query(default=None, ge=0, description="Minimum price in USD"),
    max_price_usd: Optional[float] = Query(default=None, ge=0, description="Maximum price in USD"),
    min_rarity: Optional[int] = Query(default=None, ge=1, description="Minimum rarity rank (lower is rarer)"),
    max_rarity: Optional[int] = Query(default=None, ge=1, description="Maximum rarity rank (lower is rarer)"),
):
    """
    Get paginated list of NFTs with optional filtering and sorting.
    
    - **limit**: Number of NFTs per page (1-100)
    - **skip**: Number of NFTs to skip for pagination
    - **sort_by**: Field to sort by (tokenId, name, collection, mintDate, price_eth, price_usd, rarityRank, likes, views)
    - **order**: Sort order (asc or desc)
    - **collection**: Filter by collection name
    - **blockchain**: Filter by blockchain (Ethereum, Polygon, Solana, etc.)
    - **status**: Filter by status (listed, sold, auction, not_for_sale)
    - **search**: Search in name, description, or collection
    - **min_price_eth/max_price_eth**: Filter by price range in ETH
    - **min_price_usd/max_price_usd**: Filter by price range in USD
    - **min_rarity/max_rarity**: Filter by rarity rank (lower is rarer)
    """
    try:
        all_nfts = load_data()

        # Apply filters
        filtered_nfts = filter_nfts(
            all_nfts,
            collection=collection,
            blockchain=blockchain,
            status=status,
            search=search,
            min_price_eth=min_price_eth,
            max_price_eth=max_price_eth,
            min_price_usd=min_price_usd,
            max_price_usd=max_price_usd,
            min_rarity=min_rarity,
            max_rarity=max_rarity,
        )

        # Apply sorting
        sorted_nfts = sort_nfts(filtered_nfts, sort_by=sort_by, order=order)

        # Apply pagination
        total = len(sorted_nfts)
        paginated_nfts = sorted_nfts[skip : skip + limit]

        return NFTsListResponse(
            nfts=[NFTResponse(**nft) for nft in paginated_nfts],
            total=total,
            limit=limit,
            skip=skip,
        )
    except Exception as e:
        logger.exception("Error fetching NFTs: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch NFTs")


@app.get("/collections", response_model=CollectionsListResponse)
def get_collections(
    limit: int = Query(default=20, ge=1, le=100, description="Number of collections per page"),
    skip: int = Query(default=0, ge=0, description="Number of collections to skip (pagination)"),
    sort_by: str = Query(
        default="name",
        description="Sort by: name, nft_count, min_price_eth, max_price_eth",
    ),
    order: str = Query(default="asc", description="Sort order: asc or desc"),
    search: Optional[str] = Query(default=None, description="Search in collection name"),
):
    """
    Get paginated list of NFT collections with optional search and sorting.
    Collections are derived from NFT data (unique collection names with counts and price range).
    - **limit**: Number of collections per page (1-100)
    - **skip**: Pagination offset
    - **sort_by**: name, nft_count, min_price_eth, max_price_eth
    - **order**: asc or desc
    - **search**: Filter by collection name (substring match)
    """
    try:
        all_nfts = load_data()
        paginated, total = build_collections_from_nfts(
            all_nfts,
            search=search,
            sort_by=sort_by,
            order=order,
            limit=limit,
            skip=skip,
        )
        return CollectionsListResponse(
            collections=[CollectionResponse(**c) for c in paginated],
            total=total,
            limit=limit,
            skip=skip,
        )
    except Exception as e:
        logger.exception("Error fetching collections: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch collections")


@app.get("/nfts/{nft_id}", response_model=NFTResponse)
def get_nft(nft_id: str):
    """
    Get a single NFT by ID.
    
    - **nft_id**: The unique NFT ID (e.g., nft-001, nft-002)
    """
    try:
        all_nfts = load_data()
        nft = next(
            (nft for nft in all_nfts if str(nft.get("id")) == str(nft_id)),
            None
        )

        if nft is None:
            raise HTTPException(
                status_code=404, detail=f"NFT with ID {nft_id} not found"
            )

        return NFTResponse(**nft)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching NFT %s: %s", nft_id, e)
        raise HTTPException(status_code=500, detail="Failed to fetch NFT")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "nft-api-backend"}


# -----------------------------------------------------------------------------
# Run with uvicorn
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "4000")),
    )
