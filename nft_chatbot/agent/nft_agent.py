"""
NFT Orchestrator Agent using Agno framework.
No native Agno DB - uses custom database management.
"""

from typing import List
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.groq import Groq

from nft_chatbot.tools.nft_tools import list_nfts, list_collections, get_nft_details
from nft_chatbot.agent.instructions import BASE_INSTRUCTIONS
from nft_chatbot.config import settings


def _get_model():
    """Get the appropriate model based on available API keys."""
    if settings.groq_api_key:
        return Groq(id="openai/gpt-oss-20b", api_key=settings.groq_api_key)
    elif settings.openai_api_key:
        return OpenAIChat(id=settings.openai_model, api_key=settings.openai_api_key)
    else:
        raise ValueError("No API key found. Set OPENAI_API_KEY or GROQ_API_KEY in .env")


def create_nft_agent(system_prompt: str) -> Agent:
    """
    Create NFT agent with custom context.
    
    Args:
        system_prompt: Full system prompt including user context from DB
    
    Returns:
        Configured Agno Agent
    """
    return Agent(
        name="NFT Marketplace Assistant",
        model=_get_model(),
        
        # Tools for NFT API interaction
        tools=[list_nfts, list_collections, get_nft_details],
        
        # System instructions (includes user context from our DB)
        instructions=system_prompt,
        
        # Output formatting
        markdown=True,
    )


async def run_agent_with_context(
    message: str,
    system_prompt: str,
    history: List[dict] = None
) -> str:
    """
    Run agent with pre-built context.
    
    Args:
        message: User's current message
        system_prompt: Full system prompt including memories
        history: Conversation history as list of {role, content} dicts
    
    Returns:
        Agent response content
    """
    agent = create_nft_agent(system_prompt=system_prompt)
    
    # TODO: Add history support - Agno agent needs messages to be set during initialization
    # For now, we'll rely on system prompt context which includes relevant history
    
    # Run agent with current message
    result = await agent.arun(input=message)
    
    return result.content
