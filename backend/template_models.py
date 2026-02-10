"""Pydantic models for template data validation."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class NFTPrice(BaseModel):
    """NFT price information."""
    eth: float
    usd: Optional[int] = None


class NFTOwner(BaseModel):
    """NFT owner/creator information."""
    address: str
    username: Optional[str] = None
    verified: Optional[bool] = None


class NFTAttribute(BaseModel):
    """NFT attribute/property."""
    trait_type: str
    value: str
    rarity: Optional[str] = None


class NFTHistoryEvent(BaseModel):
    """NFT history event."""
    event: str
    price: Optional[NFTPrice] = None
    from_: Optional[str] = Field(None, alias="from")
    to: Optional[str] = None
    timestamp: Optional[str] = None
    date: Optional[str] = None


class NFTStats(BaseModel):
    """NFT stats."""
    power: Optional[int] = None
    speed: Optional[int] = None
    intelligence: Optional[int] = None


class NFTGridItem(BaseModel):
    """NFT data for grid/table views."""
    id: str
    tokenId: Optional[int] = None
    name: str
    collection: str
    image: str
    thumbnail: Optional[str] = None
    price: NFTPrice
    lastSale: Optional[NFTPrice] = None
    owner: NFTOwner
    status: Literal["listed", "sold", "auction", "not_for_sale"]
    rarityRank: int
    likes: Optional[int] = 0
    views: Optional[int] = 0
    priceChange24h: Optional[float] = None
    blockchain: Optional[str] = None


class NFTDetails(NFTGridItem):
    """Extended NFT data for details view."""
    description: Optional[str] = None
    priceChange: Optional[float] = None
    highestBid: Optional[NFTPrice] = None
    creator: Optional[NFTOwner] = None
    attributes: Optional[List[NFTAttribute]] = []
    stats: Optional[NFTStats] = None
    utility: Optional[List[str]] = []
    history: Optional[List[NFTHistoryEvent]] = []
    contractAddress: Optional[str] = None
    mintDate: Optional[str] = None


class CryptoChartData(BaseModel):
    """Chart data for crypto details."""
    labels: List[str]
    prices: List[float]


class CryptoDetails(BaseModel):
    """Crypto currency data."""
    name: str
    symbol: str
    icon: Optional[str] = None
    rank: Optional[int] = None
    price: float
    priceChange24h: Optional[float] = None
    marketCap: Optional[float] = None
    marketCapChange: Optional[float] = None
    volume24h: Optional[float] = None
    volumeChange: Optional[float] = None
    circulatingSupply: Optional[float] = None
    totalSupply: Optional[float] = None
    ath: Optional[float] = None
    athChange: Optional[float] = None
    low24h: Optional[float] = None
    high24h: Optional[float] = None
    change7d: Optional[float] = None
    change30d: Optional[float] = None
    marketDominance: Optional[float] = None
    volumeMarketCapRatio: Optional[float] = None
    description: Optional[str] = None
    chartData: Optional[CryptoChartData] = None


# Export all models
__all__ = [
    "NFTPrice",
    "NFTOwner",
    "NFTAttribute",
    "NFTHistoryEvent",
    "NFTStats",
    "NFTGridItem",
    "NFTDetails",
    "CryptoChartData",
    "CryptoDetails",
]
