"""
Enhanced template agent with dynamic field selection and customizable rendering.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, Template
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("template-agent-enhanced")

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"

# Initialize Jinja2 environment
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True
)

# Add custom filters
jinja_env.filters['abs'] = abs
jinja_env.filters['round'] = round


class EnhancedTemplateRequest(BaseModel):
    """Enhanced request model with field selection."""
    template_type: Literal["nft_grid", "nft_table", "nft_details", "crypto_details", "collection_grid", "collection_table"]
    data: Dict[str, Any]
    fields_to_show: Optional[List[str]] = None  # NEW: Specify which fields to show
    detail_level: Optional[Literal["minimal", "standard", "detailed", "full"]] = "standard"  # NEW: Detail level
    custom_styles: Optional[Dict[str, str]] = None  # NEW: Custom CSS classes


class EnhancedTemplateAgent:
    """
    Enhanced template agent with dynamic field selection.
    
    Features:
    - Field filtering: Show only requested fields
    - Detail levels: minimal, standard, detailed, full
    - Custom styling: Apply custom CSS classes
    - Conditional rendering: Show/hide based on data availability
    """
    
    # Default fields for each detail level
    DETAIL_LEVELS = {
        "nft_grid": {
            "minimal": ["name", "image", "price"],
            "standard": ["name", "image", "price", "collection", "status"],
            "detailed": ["name", "image", "price", "collection", "status", "owner", "rarityRank"],
            "full": ["name", "image", "price", "collection", "status", "owner", "rarityRank", 
                    "lastSale", "likes", "views", "priceChange24h", "blockchain"]
        },
        "nft_table": {
            "minimal": ["name", "price", "status"],
            "standard": ["name", "collection", "price", "owner", "status"],
            "detailed": ["name", "collection", "price", "lastSale", "owner", "rarityRank", "status"],
            "full": ["name", "tokenId", "collection", "price", "lastSale", "owner", 
                    "rarityRank", "status", "likes", "views", "priceChange24h"]
        },
        "nft_details": {
            "minimal": ["name", "image", "price", "description"],
            "standard": ["name", "image", "price", "description", "collection", "owner", "status"],
            "detailed": ["name", "image", "price", "description", "collection", "owner", 
                        "status", "rarityRank", "lastSale", "attributes"],
            "full": "all"  # Show everything
        },
        "collection_grid": {
            "minimal": ["name", "nft_count"],
            "standard": ["name", "nft_count", "blockchains", "min_price_eth", "max_price_eth"],
            "detailed": ["name", "nft_count", "blockchains", "min_price_eth", "max_price_eth"],
            "full": ["name", "nft_count", "blockchains", "min_price_eth", "max_price_eth"],
        },
        "collection_table": {
            "minimal": ["name", "nft_count"],
            "standard": ["name", "nft_count", "blockchains", "min_price_eth", "max_price_eth"],
            "detailed": ["name", "nft_count", "blockchains", "min_price_eth", "max_price_eth"],
            "full": ["name", "nft_count", "blockchains", "min_price_eth", "max_price_eth"],
        },
    }
    
    TEMPLATE_MAP = {
        "nft_grid": "nft-grid-template.html",
        "nft_table": "nft-table-template.html",
        "nft_details": "nft-details-template.html",
        "crypto_details": "crypto-details-template.html",
        "collection_grid": "collection-grid-template.html",
        "collection_table": "collection-table-template.html",
    }
    
    def __init__(self):
        """Initialize enhanced template agent."""
        self.env = jinja_env
        logger.info("Enhanced template agent initialized")
    
    def render(self, request: EnhancedTemplateRequest) -> str:
        """
        Render template with dynamic field selection.
        
        Args:
            request: EnhancedTemplateRequest with template_type, data, and options
            
        Returns:
            Rendered HTML string
        """
        try:
            # Get template file name
            template_file = self.TEMPLATE_MAP.get(request.template_type)
            if not template_file:
                raise ValueError(f"Invalid template type: {request.template_type}")
            
            # Determine which fields to show
            fields_to_show = self._get_fields_to_show(
                request.template_type,
                request.fields_to_show,
                request.detail_level
            )
            
            # Load template
            template = self.env.get_template(template_file)
            
            # Prepare render context
            context = {
                **request.data,
                "fields_to_show": fields_to_show,
                "detail_level": request.detail_level,
                "custom_styles": request.custom_styles or {}
            }
            
            # Render with data
            html = template.render(**context)
            
            logger.info(f"Successfully rendered {request.template_type} with {len(fields_to_show)} fields")
            return html
            
        except TemplateNotFound as e:
            logger.error(f"Template not found: {e}")
            raise ValueError(f"Template file not found: {template_file}")
        
        except Exception as e:
            logger.exception(f"Error rendering template: {e}")
            raise ValueError(f"Template rendering failed: {str(e)}")
    
    def _get_fields_to_show(
        self,
        template_type: str,
        explicit_fields: Optional[List[str]],
        detail_level: str
    ) -> Set[str]:
        """
        Determine which fields to show based on explicit list or detail level.
        
        Priority:
        1. Explicit fields list (if provided)
        2. Detail level defaults
        3. Standard level defaults
        """
        # If explicit fields provided, use those
        if explicit_fields:
            return set(explicit_fields)
        
        # Get defaults for template and detail level
        template_levels = self.DETAIL_LEVELS.get(template_type, {})
        fields = template_levels.get(detail_level)
        
        # If "all", return None (show everything)
        if fields == "all":
            return set()
        
        # If no fields defined, use standard
        if not fields:
            fields = template_levels.get("standard", [])
        
        return set(fields)
    
    def render_nft_list(
        self,
        nfts: list,
        template_type: str = "nft_grid",
        detail_level: str = "standard",
        fields: Optional[List[str]] = None
    ) -> str:
        """
        Render NFT list with optional field selection.
        
        Args:
            nfts: List of NFT dictionaries
            template_type: "nft_grid" or "nft_table"
            detail_level: "minimal", "standard", "detailed", or "full"
            fields: Optional explicit list of fields to show
            
        Returns:
            Rendered HTML string
        """
        if template_type not in ["nft_grid", "nft_table"]:
            template_type = "nft_grid"
        
        request = EnhancedTemplateRequest(
            template_type=template_type,
            data={"nfts": nfts},
            fields_to_show=fields,
            detail_level=detail_level
        )
        
        try:
            return self.render(request)
        except Exception as e:
            logger.error(f"Rendering failed: {e}")
            return self._error_html(str(e))
    
    def render_nft_details(
        self,
        nft: dict,
        detail_level: str = "standard",
        fields: Optional[List[str]] = None
    ) -> str:
        """
        Render single NFT details with optional field selection.

        Args:
            nft: NFT dictionary
            detail_level: "minimal", "standard", "detailed", or "full"
            fields: Optional explicit list of fields to show

        Returns:
            Rendered HTML string
        """
        request = EnhancedTemplateRequest(
            template_type="nft_details",
            data={"nft": nft},
            fields_to_show=fields,
            detail_level=detail_level
        )

        try:
            return self.render(request)
        except Exception as e:
            logger.error(f"Rendering failed: {e}")
            return self._error_html(str(e))

    def render_collection_list(
        self,
        collections: list,
        template_type: str = "collection_grid",
        detail_level: str = "standard",
    ) -> str:
        """
        Render collection list as grid or table.

        Args:
            collections: List of collection dicts (name, nft_count, blockchains, min_price_eth, max_price_eth)
            template_type: "collection_grid" or "collection_table"
            detail_level: "minimal", "standard", "detailed", or "full"

        Returns:
            Rendered HTML string
        """
        if template_type not in ("collection_grid", "collection_table"):
            template_type = "collection_grid"
        request = EnhancedTemplateRequest(
            template_type=template_type,
            data={"collections": collections},
            detail_level=detail_level,
        )
        try:
            return self.render(request)
        except Exception as e:
            logger.error(f"Collection list rendering failed: {e}")
            return self._error_html(str(e))

    @staticmethod
    def _error_html(error_message: str) -> str:
        """Generate error HTML."""
        return f"""
<div class="bg-red-900/20 border border-red-500 rounded-lg p-4 my-4">
    <h3 class="text-red-400 font-semibold mb-2">Template Rendering Error</h3>
    <p class="text-gray-300 text-sm">{error_message}</p>
</div>
        """


# Singleton instance
enhanced_agent = EnhancedTemplateAgent()


# Convenience functions
def render_nft_list_smart(
    nfts: list,
    user_query: str = "",
    template_type: str = "nft_grid"
) -> str:
    """
    Intelligently render NFT list based on user query.
    
    This function analyzes the user query to determine:
    - Which fields to show
    - What detail level to use
    - Which template type is best
    
    Args:
        nfts: List of NFT dictionaries
        user_query: User's original query
        template_type: Preferred template type
        
    Returns:
        Rendered HTML string
    """
    # Analyze query for detail level
    detail_level = "standard"
    explicit_fields = None
    
    query_lower = user_query.lower()
    
    # Detect detail level from query
    if any(word in query_lower for word in ["brief", "quick", "summary", "just"]):
        detail_level = "minimal"
    elif any(word in query_lower for word in ["detailed", "full", "complete", "all info", "everything"]):
        detail_level = "full"
    elif any(word in query_lower for word in ["more info", "details", "about"]):
        detail_level = "detailed"
    
    # Detect specific field requests
    field_keywords = {
        "price": ["price", "cost", "value"],
        "owner": ["owner", "owned by", "belongs to"],
        "rarityRank": ["rarity", "rank", "rare"],
        "attributes": ["attributes", "traits", "properties"],
        "lastSale": ["last sale", "previous sale", "sold for"],
        "likes": ["likes", "popular", "popularity"],
        "views": ["views", "traffic"],
        "blockchain": ["blockchain", "chain", "network"],
        "status": ["status", "available", "listed"],
    }
    
    mentioned_fields = set()
    for field, keywords in field_keywords.items():
        if any(kw in query_lower for kw in keywords):
            mentioned_fields.add(field)
    
    # If specific fields mentioned, use those
    if mentioned_fields:
        # Always include basic fields
        explicit_fields = list({"name", "image", "price", "collection"} | mentioned_fields)
    
    return enhanced_agent.render_nft_list(
        nfts=nfts,
        template_type=template_type,
        detail_level=detail_level,
        fields=explicit_fields
    )


__all__ = [
    "EnhancedTemplateAgent",
    "EnhancedTemplateRequest",
    "enhanced_agent",
    "render_nft_list_smart",
]
