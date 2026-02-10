"""
NFT Website Chatbot — Production-grade Agno AI agent with FastAPI.

This is the legacy entry point. For new usage, import from nft_chatbot.main.
"""

from nft_chatbot.main import app, main

__all__ = ["app", "main"]

if __name__ == "__main__":
    main()
