"""
Lightweight template-filling agent for rendering NFT/crypto HTML templates.
No memory, no session storage - purely stateless template rendering.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("template-agent")

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
    
    def render_nft_list(self, nfts: list, template_type: str = "nft_grid") -> str:
        """
        Convenience method to render NFT list.
        
        Args:
            nfts: List of NFT dictionaries
            template_type: Either "nft_grid" or "nft_table"
            
        Returns:
            Rendered HTML string
        """
        if template_type not in ["nft_grid", "nft_table"]:
            template_type = "nft_grid"
        
        request = TemplateRequest(
            template_type=template_type,
            data={"nfts": nfts}
        )
        return self.render_safe(request)
    
    def render_nft_details(self, nft: dict) -> str:
        """
        Convenience method to render single NFT details.
        
        Args:
            nft: NFT dictionary
            
        Returns:
            Rendered HTML string
        """
        request = TemplateRequest(
            template_type="nft_details",
            data={"nft": nft}
        )
        return self.render_safe(request)
    
    def render_crypto_details(self, crypto: dict) -> str:
        """
        Convenience method to render crypto details.
        
        Args:
            crypto: Crypto dictionary
            
        Returns:
            Rendered HTML string
        """
        request = TemplateRequest(
            template_type="crypto_details",
            data={"crypto": crypto}
        )
        return self.render_safe(request)


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


def render_nft_list(nfts: list, template_type: str = "nft_grid") -> str:
    """
    Render NFT list template.
    
    Args:
        nfts: List of NFT dictionaries
        template_type: Either "nft_grid" or "nft_table"
        
    Returns:
        Rendered HTML string
    """
    return template_agent.render_nft_list(nfts, template_type)


def render_nft_details(nft: dict) -> str:
    """
    Render single NFT details template.
    
    Args:
        nft: NFT dictionary
        
    Returns:
        Rendered HTML string
    """
    return template_agent.render_nft_details(nft)


def render_crypto_details(crypto: dict) -> str:
    """
    Render crypto details template.
    
    Args:
        crypto: Crypto dictionary
        
    Returns:
        Rendered HTML string
    """
    return template_agent.render_crypto_details(crypto)


# Export main functions
__all__ = [
    "TemplateAgent",
    "TemplateRequest",
    "template_agent",
    "render_template",
    "render_nft_list",
    "render_nft_details",
    "render_crypto_details",
]
