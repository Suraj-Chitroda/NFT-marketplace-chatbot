"""
Integration module showing how to use template agent with NFT chatbot.
This demonstrates how the main chatbot can use the template agent to render rich HTML responses.
"""

import logging
from typing import Any, Dict

from template_agent import render_nft_list, render_nft_details

logger = logging.getLogger("chatbot-template-integration")


class ChatbotTemplateIntegration:
    """Integration layer between chatbot and template agent."""
    
    @staticmethod
    def should_use_template(query: str, tool_response: Dict[str, Any]) -> bool:
        """
        Determine if response should use templates.
        
        Args:
            query: User query
            tool_response: Response from tool call
            
        Returns:
            True if template should be used
        """
        # Use template for NFT list responses
        if "nfts" in tool_response and isinstance(tool_response["nfts"], list):
            return len(tool_response["nfts"]) > 0
        
        # Use template for single NFT details
        if "id" in tool_response and "collection" in tool_response:
            return True
        
        return False
    
    @staticmethod
    def render_response(query: str, tool_response: Dict[str, Any]) -> str:
        """
        Render tool response using appropriate template.
        
        Args:
            query: User query
            tool_response: Response from tool call (API data)
            
        Returns:
            HTML string or plain text if template not applicable
        """
        # NFT List Response
        if "nfts" in tool_response and isinstance(tool_response["nfts"], list):
            nfts = tool_response["nfts"]
            
            if len(nfts) == 0:
                return "<div class='message'><p>No NFTs found matching your criteria.</p></div>"
            
            # Determine template type (grid vs table)
            # Use table for large lists or when user mentions "table"
            if len(nfts) > 12 or "table" in query.lower():
                template_type = "nft_table"
            else:
                template_type = "nft_grid"
            
            # Add contextual message
            count = tool_response.get("total", len(nfts))
            html = f"<div class='nft-response'><p>Found {count} NFTs. Showing {len(nfts)}:</p></div>\n"
            html += render_nft_list(nfts, template_type=template_type)
            
            return html
        
        # Single NFT Details Response
        if "id" in tool_response and "collection" in tool_response and "nfts" not in tool_response:
            html = render_nft_details(tool_response)
            return html
        
        # Fallback: Return as formatted text
        return f"<div class='message'><pre>{tool_response}</pre></div>"
    
    @staticmethod
    def wrap_text_response(text: str) -> str:
        """Wrap plain text in HTML."""
        return f"<div class='message'><p>{text}</p></div>"
    
    @staticmethod
    def wrap_error_response(error: str) -> str:
        """Wrap error in HTML."""
        return f"<div class='error-message'><p>{error}</p></div>"


# Singleton instance
integration = ChatbotTemplateIntegration()


# Convenience functions
def render_chatbot_response(query: str, tool_response: Dict[str, Any]) -> str:
    """
    Main function to render chatbot response with templates.
    
    Args:
        query: User query string
        tool_response: Tool call result (NFT data from API)
        
    Returns:
        HTML formatted response
    """
    return integration.render_response(query, tool_response)


def should_use_template(query: str, tool_response: Dict[str, Any]) -> bool:
    """Check if template should be used for response."""
    return integration.should_use_template(query, tool_response)


# Example usage
if __name__ == "__main__":
    print("Template Integration Examples\n")
    
    # Example 1: NFT List
    print("Example 1: NFT List Response")
    sample_list_response = {
        "nfts": [
            {
                "id": "nft-001",
                "name": "Test NFT #1",
                "collection": "Test Collection",
                "image": "https://example.com/img1.png",
                "thumbnail": "https://example.com/img1.png",
                "price": {"eth": 1.5, "usd": 3750},
                "owner": {"address": "0x1234"},
                "status": "listed",
                "rarityRank": 100,
                "blockchain": "Ethereum"
            }
        ],
        "total": 1,
        "limit": 20,
        "skip": 0
    }
    
    html = render_chatbot_response("show me NFTs", sample_list_response)
    print(f"Rendered: {len(html)} chars")
    print(f"Is HTML: {html.startswith('<div')}\n")
    
    # Example 2: Single NFT
    print("Example 2: Single NFT Details")
    sample_nft = {
        "id": "nft-001",
        "name": "Test NFT #1",
        "collection": "Test Collection",
        "image": "https://example.com/img1.png",
        "price": {"eth": 1.5, "usd": 3750},
        "creator": {"address": "0xCreator", "username": "artist"},
        "owner": {"address": "0x1234", "username": "collector"},
        "status": "listed",
        "rarityRank": 100,
        "blockchain": "Ethereum",
        "attributes": [],
        "history": []
    }
    
    html = render_chatbot_response("show details", sample_nft)
    print(f"Rendered: {len(html)} chars")
    print(f"Is HTML: {html.startswith('<div')}\n")
    
    print("✅ Integration examples completed")
