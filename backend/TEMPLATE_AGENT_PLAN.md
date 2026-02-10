# Template Data-Filling Agent Plan

## Overview
This document outlines the design and implementation plan for a **lightweight template-filling agent** that renders HTML templates with dynamic NFT/crypto data without memory or session storage.

---

## 1. Agent Purpose & Requirements

### Primary Purpose
- Receive NFT or crypto data from the main chatbot agent
- Select the appropriate HTML template
- Fill template with dynamic data
- Return rendered HTML response

### Key Requirements
- **No Memory**: Agent is stateless, doesn't store request/response data
- **No Session Management**: Each request is independent
- **Lightweight**: Fast rendering, minimal processing
- **Single Responsibility**: Only template rendering, no business logic
- **Template Agnostic**: Works with Jinja2 templates

---

## 2. Architecture

### Flow Diagram
```
Main Chatbot Agent
    ↓ (detects NFT/crypto query)
    ↓ (calls API to get data)
    ↓
Template Filling Agent
    ↓ (receives data + template type)
    ↓ (renders template with Jinja2)
    ↓ (returns HTML string)
    ↓
Main Chatbot Agent
    ↓ (returns HTML to user)
```

### Components
1. **Template Selector**: Chooses template based on data type
2. **Data Validator**: Ensures data structure matches template expectations
3. **Template Renderer**: Jinja2 rendering engine
4. **Error Handler**: Returns fallback HTML on errors

---

## 3. Data Structures

### Input Format
```python
{
    "template_type": "nft_grid" | "nft_table" | "nft_details" | "crypto_details",
    "data": {
        # NFT Grid/Table: array of NFTs
        "nfts": [ ... ],
        
        # NFT Details: single NFT object
        "nft": { ... },
        
        # Crypto Details: single crypto object
        "crypto": { ... }
    }
}
```

### NFT Data Structure (for grid/table)
```python
{
    "id": "nft-001",
    "tokenId": 1,
    "name": "NFT Name #001",
    "collection": "Collection Name",
    "image": "https://...",
    "thumbnail": "https://...",
    "price": {
        "eth": 1.25,
        "usd": 3120
    },
    "lastSale": {
        "eth": 1.1,
        "date": "2024-02-01T18:40:00Z"
    },
    "owner": {
        "address": "0x1234...5678",
        "username": "cryptoKing"
    },
    "status": "listed" | "sold" | "auction" | "not_for_sale",
    "rarityRank": 128,
    "likes": 342,
    "views": 4120,
    "priceChange24h": 12.5  # optional
}
```

### NFT Data Structure (for details)
```python
{
    "id": "nft-001",
    "name": "NFT Name #001",
    "collection": "Collection Name",
    "description": "Description text...",
    "image": "https://...",
    "thumbnail": "https://...",
    "price": {
        "eth": 2.45,
        "usd": 4523.50
    },
    "priceChange": 12.5,
    "lastSale": {
        "eth": 2.10
    },
    "highestBid": {
        "eth": 2.30
    },
    "creator": {
        "address": "0xArtist...1234",
        "username": "artist",
        "verified": true
    },
    "owner": {
        "address": "0x1234...5678",
        "username": "collector"
    },
    "views": 1234,
    "likes": 89,
    "status": "listed",
    "rarityRank": 128,
    "attributes": [
        {
            "trait_type": "Background",
            "value": "Cosmic Purple",
            "rarity": "12%"
        }
    ],
    "history": [
        {
            "event": "Sale",
            "price": {
                "eth": 2.10
            },
            "from": "0xSeller...",
            "to": "0xBuyer...",
            "timestamp": "2 hours ago"
        }
    ]
}
```

### Crypto Data Structure
```python
{
    "name": "Bitcoin",
    "symbol": "BTC",
    "icon": "₿",  # optional emoji/character
    "rank": 1,
    "price": 43567.89,
    "priceChange24h": 5.23,
    "marketCap": 847200000000,
    "marketCapChange": 2.1,
    "volume24h": 28500000000,
    "volumeChange": 15.3,
    "circulatingSupply": 19400000,
    "totalSupply": 21000000,
    "ath": 69044,
    "athChange": -36.9,
    "low24h": 41234.56,
    "high24h": 44567.89,
    "change7d": 12.4,
    "change30d": -5.2,
    "marketDominance": 48.2,
    "volumeMarketCapRatio": 3.36,
    "description": "Brief description...",
    "chartData": {
        "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "prices": [41200, 42500, 41800, 43200, 42800, 44100, 43567]
    }
}
```

---

## 4. Implementation

### File Structure
```
backend/
├── templates/
│   ├── nft-grid-template.html
│   ├── nft-table-template.html
│   ├── nft-details-template.html
│   └── crypto-details-template.html
├── template_agent.py          # Main agent logic
├── template_models.py          # Pydantic models for validation
└── template_utils.py           # Helper functions
```

### Core Code: `template_agent.py`

```python
"""
Lightweight template-filling agent for rendering NFT/crypto HTML templates.
No memory, no session storage - purely stateless template rendering.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Literal

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("template-agent")

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"

# Initialize Jinja2 environment
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True
)

# Add custom filters
jinja_env.filters['abs'] = abs
jinja_env.filters['round'] = round


class TemplateRequest(BaseModel):
    """Request model for template rendering."""
    template_type: Literal["nft_grid", "nft_table", "nft_details", "crypto_details"]
    data: Dict[str, Any]


class TemplateAgent:
    """Lightweight agent for filling templates with dynamic data."""
    
    TEMPLATE_MAP = {
        "nft_grid": "nft-grid-template.html",
        "nft_table": "nft-table-template.html",
        "nft_details": "nft-details-template.html",
        "crypto_details": "crypto-details-template.html",
    }
    
    def __init__(self):
        """Initialize template agent."""
        self.env = jinja_env
        logger.info("Template agent initialized")
    
    def render(self, request: TemplateRequest) -> str:
        """
        Render template with provided data.
        
        Args:
            request: TemplateRequest with template_type and data
            
        Returns:
            Rendered HTML string
            
        Raises:
            ValueError: If template type is invalid or rendering fails
        """
        try:
            # Get template file name
            template_file = self.TEMPLATE_MAP.get(request.template_type)
            if not template_file:
                raise ValueError(f"Invalid template type: {request.template_type}")
            
            # Load template
            template = self.env.get_template(template_file)
            
            # Render with data
            html = template.render(**request.data)
            
            logger.info(f"Successfully rendered {request.template_type}")
            return html
            
        except TemplateNotFound as e:
            logger.error(f"Template not found: {e}")
            raise ValueError(f"Template file not found: {template_file}")
        
        except Exception as e:
            logger.exception(f"Error rendering template: {e}")
            raise ValueError(f"Template rendering failed: {str(e)}")
    
    def render_safe(self, request: TemplateRequest) -> str:
        """
        Render template with error handling and fallback.
        
        Args:
            request: TemplateRequest with template_type and data
            
        Returns:
            Rendered HTML string or error HTML
        """
        try:
            return self.render(request)
        except Exception as e:
            logger.error(f"Rendering failed, returning error HTML: {e}")
            return self._error_html(str(e))
    
    @staticmethod
    def _error_html(error_message: str) -> str:
        """Generate error HTML."""
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Rendering Error</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-900 text-white min-h-screen flex items-center justify-center">
            <div class="max-w-md p-6 bg-red-900/20 border border-red-500 rounded-lg">
                <h2 class="text-xl font-bold mb-2">Template Rendering Error</h2>
                <p class="text-gray-300">{error_message}</p>
            </div>
        </body>
        </html>
        """


# Singleton instance
template_agent = TemplateAgent()


def render_template(template_type: str, data: Dict[str, Any]) -> str:
    """
    Convenience function to render a template.
    
    Args:
        template_type: Type of template to render
        data: Data to fill template with
        
    Returns:
        Rendered HTML string
    """
    request = TemplateRequest(template_type=template_type, data=data)
    return template_agent.render_safe(request)
```

### Pydantic Models: `template_models.py`

```python
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


class NFTDetails(NFTGridItem):
    """Extended NFT data for details view."""
    description: Optional[str] = None
    priceChange: Optional[float] = None
    highestBid: Optional[NFTPrice] = None
    creator: Optional[NFTOwner] = None
    attributes: Optional[List[NFTAttribute]] = []
    history: Optional[List[NFTHistoryEvent]] = []


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
```

---

## 5. Integration with Main Chatbot

### How Main Agent Uses Template Agent

```python
# In main chatbot agent logic

from backend.template_agent import render_template
from backend.template_models import NFTGridItem, CryptoDetails

def handle_nft_query(user_query: str) -> str:
    """Handle NFT-related query."""
    
    # 1. Determine intent (grid view, table view, or details)
    if "list" in user_query or "show all" in user_query:
        template_type = "nft_grid"
    elif "table" in user_query:
        template_type = "nft_table"
    else:
        template_type = "nft_details"
    
    # 2. Call backend API to get NFT data
    nft_data = call_nft_api(user_query)
    
    # 3. Validate and transform data
    if template_type in ["nft_grid", "nft_table"]:
        validated_nfts = [NFTGridItem(**nft).dict() for nft in nft_data]
        data = {"nfts": validated_nfts}
    else:
        validated_nft = NFTDetails(**nft_data).dict()
        data = {"nft": validated_nft}
    
    # 4. Render template
    html = render_template(template_type, data)
    
    # 5. Return HTML (or wrap with text response)
    return f"Here are the NFTs you requested:\n\n{html}"


def handle_crypto_query(symbol: str) -> str:
    """Handle crypto price query."""
    
    # 1. Call crypto API
    crypto_data = call_crypto_api(symbol)
    
    # 2. Validate data
    validated_crypto = CryptoDetails(**crypto_data).dict()
    
    # 3. Render template
    html = render_template("crypto_details", {"crypto": validated_crypto})
    
    return f"Here's the information for {symbol}:\n\n{html}"
```

### FastAPI Endpoint (Optional)

```python
# Add to backend API for direct template rendering

from fastapi import FastAPI, HTTPException
from backend.template_agent import template_agent, TemplateRequest

app = FastAPI()

@app.post("/render-template")
async def render_template_endpoint(request: TemplateRequest):
    """
    Render template with provided data.
    
    POST /render-template
    {
        "template_type": "nft_grid",
        "data": {
            "nfts": [...]
        }
    }
    """
    try:
        html = template_agent.render(request)
        return {"html": html}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 6. Testing

### Unit Tests

```python
# tests/test_template_agent.py

import pytest
from backend.template_agent import TemplateAgent, TemplateRequest

def test_render_nft_grid():
    """Test NFT grid template rendering."""
    agent = TemplateAgent()
    request = TemplateRequest(
        template_type="nft_grid",
        data={
            "nfts": [
                {
                    "id": "nft-001",
                    "name": "Test NFT #1",
                    "collection": "Test Collection",
                    "image": "https://example.com/image.png",
                    "price": {"eth": 1.5, "usd": 3000},
                    "owner": {"address": "0x1234"},
                    "status": "listed",
                    "rarityRank": 100
                }
            ]
        }
    )
    
    html = agent.render(request)
    assert "Test NFT #1" in html
    assert "1.5" in html
    assert "Test Collection" in html


def test_render_invalid_template():
    """Test error handling for invalid template."""
    agent = TemplateAgent()
    request = TemplateRequest(
        template_type="invalid_template",
        data={}
    )
    
    with pytest.raises(ValueError):
        agent.render(request)


def test_render_safe_returns_error_html():
    """Test safe rendering returns error HTML on failure."""
    agent = TemplateAgent()
    request = TemplateRequest(
        template_type="nft_grid",
        data={}  # Missing required data
    )
    
    html = agent.render_safe(request)
    assert "error" in html.lower() or "<!DOCTYPE html>" in html
```

---

## 7. Deployment Considerations

### Performance
- **Template Caching**: Jinja2 automatically caches compiled templates
- **Data Validation**: Use Pydantic for fast validation
- **No I/O**: Agent is stateless, no database or file I/O

### Scalability
- Agent is stateless and can be scaled horizontally
- No shared state between requests
- Can run in serverless environments

### Security
- **Autoescape**: Jinja2 autoescape is enabled to prevent XSS
- **Input Validation**: All data validated with Pydantic
- **No User Input in Templates**: Templates don't execute user-provided code

---

## 8. Future Enhancements

1. **Template Versioning**: Support multiple template versions
2. **Theme Support**: Allow theme switching (dark/light mode)
3. **Partial Rendering**: Render only components instead of full pages
4. **Caching Layer**: Add Redis cache for frequently rendered templates
5. **Template Preview**: Add preview endpoint for template testing
6. **Custom Filters**: Add more Jinja2 filters for data formatting

---

## 9. Summary

The Template Data-Filling Agent is a **lightweight, stateless service** that:
- ✅ Renders Jinja2 templates with dynamic NFT/crypto data
- ✅ No memory or session storage
- ✅ Fast and scalable
- ✅ Well-validated inputs with Pydantic
- ✅ Easy integration with main chatbot agent
- ✅ Production-ready error handling

Use this agent whenever the main chatbot needs to display NFT or crypto data in a rich HTML format!
