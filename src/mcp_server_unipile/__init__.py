import argparse
import asyncio
import logging
import os
from typing import Optional
from . import server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    """
    Main entry point for the unipile MCP Server.
    Uses UNIPILE_DSN and UNIPILE_API_KEY environment variables for authentication.
    """
    logger.info("Starting mcp-server-unipile")
    
    dsn = os.getenv("UNIPILE_DSN")
    api_key = os.getenv("UNIPILE_API_KEY")
    
    if not dsn:
        logger.error("UNIPILE_DSN environment variable is required")
        raise ValueError("UNIPILE_DSN environment variable must be set")
        
    if not api_key:
        logger.error("UNIPILE_API_KEY environment variable is required")
        raise ValueError("UNIPILE_API_KEY environment variable must be set")
    
    logger.info("Starting server with provided credentials")
    asyncio.run(server.main(dsn=dsn, api_key=api_key))
    logger.info("Server shutdown complete")

if __name__ == "__main__":
    main()

# Expose important items at package level
__all__ = ["main", "server"] 