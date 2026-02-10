"""
FastAPI application for template rendering service.
Lightweight, stateless template-filling API.
"""

import logging
import os
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from template_agent import template_agent, TemplateRequest
from template_models import NFTGridItem, NFTDetails, CryptoDetails

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("template-api")

# Create FastAPI app
app = FastAPI(
    title="Template Rendering API",
    version="1.0.0",
    description="Lightweight, stateless template rendering service for NFT and crypto data",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class RenderRequest(BaseModel):
    """Request model for template rendering."""
    template_type: Literal["nft_grid", "nft_table", "nft_details", "crypto_details"]
    data: Dict[str, Any]


class RenderResponse(BaseModel):
    """Response model for template rendering."""
    html: str
    template_type: str
    length: int


class NFTListRenderRequest(BaseModel):
    """Request model for NFT list rendering."""
    nfts: List[Dict[str, Any]]
    template_type: Literal["nft_grid", "nft_table"] = "nft_grid"


class NFTDetailsRenderRequest(BaseModel):
    """Request model for NFT details rendering."""
    nft: Dict[str, Any]


class CryptoDetailsRenderRequest(BaseModel):
    """Request model for crypto details rendering."""
    crypto: Dict[str, Any]


# Endpoints
@app.post("/render", response_model=RenderResponse)
async def render_template_endpoint(request: RenderRequest):
    """
    Render any template with provided data.
    
    POST /render
    {
        "template_type": "nft_grid",
        "data": {
            "nfts": [...]
        }
    }
    """
    try:
        template_request = TemplateRequest(
            template_type=request.template_type,
            data=request.data
        )
        html = template_agent.render_safe(template_request)
        
        return RenderResponse(
            html=html,
            template_type=request.template_type,
            length=len(html)
        )
    except Exception as e:
        logger.exception("Template rendering error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/render/nft-list", response_class=HTMLResponse)
async def render_nft_list_endpoint(request: NFTListRenderRequest):
    """
    Render NFT list (grid or table).
    
    POST /render/nft-list
    {
        "nfts": [...],
        "template_type": "nft_grid"
    }
    """
    try:
        html = template_agent.render_nft_list(
            request.nfts,
            template_type=request.template_type
        )
        return html
    except Exception as e:
        logger.exception("NFT list rendering error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/render/nft-details", response_class=HTMLResponse)
async def render_nft_details_endpoint(request: NFTDetailsRenderRequest):
    """
    Render single NFT details.
    
    POST /render/nft-details
    {
        "nft": {...}
    }
    """
    try:
        html = template_agent.render_nft_details(request.nft)
        return html
    except Exception as e:
        logger.exception("NFT details rendering error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/render/crypto-details", response_class=HTMLResponse)
async def render_crypto_details_endpoint(request: CryptoDetailsRenderRequest):
    """
    Render crypto details.
    
    POST /render/crypto-details
    {
        "crypto": {...}
    }
    """
    try:
        html = template_agent.render_crypto_details(request.crypto)
        return html
    except Exception as e:
        logger.exception("Crypto details rendering error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "template-rendering-api",
        "templates": list(template_agent.TEMPLATE_MAP.keys())
    }


@app.get("/templates")
def list_templates():
    """List available templates."""
    return {
        "templates": [
            {
                "type": template_type,
                "file": template_file,
                "description": f"Template for {template_type.replace('_', ' ')}"
            }
            for template_type, template_file in template_agent.TEMPLATE_MAP.items()
        ]
    }


# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("TEMPLATE_API_PORT", "5000"))
    
    logger.info(f"Starting template API on port {port}")
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=port,
    )
