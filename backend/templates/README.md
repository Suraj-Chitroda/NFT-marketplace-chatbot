# NFT & Crypto HTML Templates

## Overview
This folder contains **cleaned, production-ready HTML templates** for displaying NFT and cryptocurrency data. All templates use **Jinja2 syntax** for dynamic data filling and are designed to be rendered by a lightweight, stateless agent.

## Templates

### 1. `nft-grid-template.html`
**Purpose**: Display multiple NFTs in a responsive grid layout

**Expected Data**:
```python
{
    "nfts": [
        {
            "id": "nft-001",
            "name": "NFT Name",
            "collection": "Collection Name",
            "image": "image_url",
            "price": {"eth": 1.25, "usd": 3120},
            "lastSale": {"eth": 1.1},
            "owner": {"address": "0x..."},
            "status": "listed",
            "rarityRank": 128,
            ...
        }
    ]
}
```

**Features**:
- Responsive 1-4 column grid
- Hover effects with buy button
- Rarity badges (Legendary/Mythic/Rare/Epic)
- Price display with optional 24h change
- Owner address truncation

---

### 2. `nft-table-template.html`
**Purpose**: Display multiple NFTs in a sortable table format

**Expected Data**:
```python
{
    "nfts": [
        {
            "id": "nft-001",
            "name": "NFT Name",
            "collection": "Collection Name",
            "thumbnail": "thumbnail_url",
            "price": {"eth": 1.25},
            "lastSale": {"eth": 1.1},
            "priceChange24h": 12.5,
            "rarityRank": 128,
            "owner": {"address": "0x..."},
            ...
        }
    ]
}
```

**Features**:
- Compact table layout
- Thumbnail + name display
- Price change indicators (up/down arrows)
- Rarity badges
- View action buttons

---

### 3. `nft-details-template.html`
**Purpose**: Display detailed information for a single NFT

**Expected Data**:
```python
{
    "nft": {
        "id": "nft-001",
        "name": "NFT Name",
        "collection": "Collection Name",
        "image": "full_image_url",
        "description": "NFT description",
        "price": {"eth": 2.45, "usd": 4523.50},
        "creator": {"address": "0x...", "username": "artist"},
        "owner": {"address": "0x...", "username": "collector"},
        "attributes": [
            {"trait_type": "Background", "value": "Blue", "rarity": "12%"}
        ],
        "history": [
            {"event": "Sale", "price": {"eth": 2.10}, "timestamp": "2 hours ago"}
        ],
        ...
    }
}
```

**Features**:
- Two-column layout (image + details)
- Properties/attributes grid
- Creator and owner info
- Price card with buy/offer buttons
- Stats grid (last sale, highest bid, views, likes)
- Activity history timeline

---

### 4. `crypto-details-template.html`
**Purpose**: Display detailed cryptocurrency price and market data

**Expected Data**:
```python
{
    "crypto": {
        "name": "Bitcoin",
        "symbol": "BTC",
        "icon": "₿",
        "rank": 1,
        "price": 43567.89,
        "priceChange24h": 5.23,
        "marketCap": 847200000000,
        "volume24h": 28500000000,
        "circulatingSupply": 19400000,
        "chartData": {
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "prices": [41200, 42500, 41800, 43200, 42800, 44100, 43567]
        },
        ...
    }
}
```

**Features**:
- Three-column layout
- Interactive price chart (Chart.js)
- Market statistics cards
- Currency converter
- Price statistics table
- About section

---

## Template Design

### Removed Elements
All templates have been **cleaned** and no longer contain:
- ❌ Headers with navigation
- ❌ Footers
- ❌ Static dummy data
- ❌ Hardcoded prices, names, addresses
- ❌ Connect wallet buttons

### What Remains
- ✅ Core HTML structure
- ✅ Tailwind CSS styling
- ✅ Responsive layouts
- ✅ Jinja2 template variables
- ✅ Conditional rendering logic
- ✅ Loop structures for arrays

---

## Usage

### Basic Rendering (Python)

```python
from jinja2 import Environment, FileSystemLoader

# Setup Jinja2
env = Environment(loader=FileSystemLoader('templates'))

# Load template
template = env.get_template('nft-grid-template.html')

# Prepare data
data = {
    "nfts": [
        {
            "id": "nft-001",
            "name": "Cool NFT #1",
            "collection": "Cool Collection",
            "image": "https://example.com/nft1.png",
            "price": {"eth": 1.5, "usd": 3000},
            "owner": {"address": "0x1234567890abcdef"},
            "status": "listed",
            "rarityRank": 50
        }
    ]
}

# Render
html = template.render(**data)
print(html)
```

### With FastAPI

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

app = FastAPI()
env = Environment(loader=FileSystemLoader('templates'))

@app.get("/nfts", response_class=HTMLResponse)
async def get_nfts():
    # Get data from your backend
    nfts_data = get_nfts_from_backend()
    
    # Render template
    template = env.get_template('nft-grid-template.html')
    html = template.render(nfts=nfts_data)
    
    return html
```

---

## Data Validation

Use Pydantic models to validate data before rendering:

```python
from pydantic import BaseModel
from typing import List, Optional

class NFTPrice(BaseModel):
    eth: float
    usd: Optional[int] = None

class NFTOwner(BaseModel):
    address: str
    username: Optional[str] = None

class NFTGridItem(BaseModel):
    id: str
    name: str
    collection: str
    image: str
    price: NFTPrice
    owner: NFTOwner
    status: str
    rarityRank: int

# Validate before rendering
validated_nfts = [NFTGridItem(**nft).dict() for nft in raw_nfts]
html = template.render(nfts=validated_nfts)
```

---

## Styling

All templates use:
- **Tailwind CSS** (CDN) for styling
- **Inter font** from Google Fonts
- **Dark theme** with custom color palette:
  - Background: `hsl(222, 47%, 6%)`
  - Primary: `hsl(199, 89%, 48%)`
  - Accent: `hsl(270, 80%, 60%)`
  - Success: `hsl(142, 76%, 45%)`
  - Destructive: `hsl(0, 84%, 60%)`

### Glass Card Effect
```css
.glass-card {
  background: linear-gradient(145deg, hsl(222, 47%, 11%) 0%, hsl(222, 47%, 8%) 100%);
  backdrop-filter: blur(12px);
}
```

---

## Integration Plan

See **`TEMPLATE_AGENT_PLAN.md`** for complete implementation guide including:
- Lightweight template-filling agent design
- Data structure specifications
- Pydantic validation models
- Integration with main chatbot
- Testing strategies
- Deployment considerations

---

## Notes

- Templates use **Jinja2 syntax**: `{{ variable }}`, `{% if %}`, `{% for %}`
- All templates are **mobile-responsive**
- **Autoescape is enabled** for XSS protection
- Chart data uses **Chart.js** (crypto template only)
- Rarity calculation based on `rarityRank` value:
  - Legendary: rank ≤ 100
  - Mythic: rank ≤ 300
  - Rare: rank ≤ 500
  - Epic: rank > 500

---

## License
Templates are part of the NFT Chatbot project and follow the project's license terms.
