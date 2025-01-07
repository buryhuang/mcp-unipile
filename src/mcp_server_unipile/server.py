import os
import json
import logging
from typing import Any, Optional
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from pydantic import AnyUrl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .unipile_client import UnipileClient

class UnipileWrapper:
    def __init__(self, dsn: Optional[str] = None, api_key: Optional[str] = None):
        dsn = dsn or os.getenv("UNIPILE_DSN")
        api_key = api_key or os.getenv("UNIPILE_API_KEY")
        
        logger.debug(f"Using DSN: {'[MASKED]' if dsn else 'None'}")
        if not dsn:
            raise ValueError("UNIPILE_DSN environment variable is required")
            
        logger.debug(f"Using API key: {'[MASKED]' if api_key else 'None'}")
        if not api_key:
            raise ValueError("UNIPILE_API_KEY environment variable is required")
        
        self.client = UnipileClient(dsn=dsn, api_key=api_key)

    def get_accounts(self) -> str:
        """Get all connected accounts"""
        try:
            accounts = self.client.get_accounts()
            logger.info(f"Accounts: {accounts}")
            logger.info(f"Accounts Json: {json.dumps(accounts, default=str)}")
            return json.dumps(accounts, default=str)
        except Exception as e:
            logger.error(f"Error getting accounts: {str(e)}")
            return json.dumps({"error": str(e)})

    def get_chats(self) -> str:
        """Get all available chats"""
        try:
            chats = self.client.get_chats()
            return json.dumps(chats)
        except Exception as e:
            logger.error(f"Error getting chats: {str(e)}")
            return json.dumps({"error": str(e)})

    def get_chat_messages(self, chat_id: str, batch_size: int = 100) -> str:
        """Get all messages from a chat"""
        try:
            messages = self.client.get_messages_as_list(chat_id, batch_size)
            return json.dumps(messages)
        except Exception as e:
            logger.error(f"Error getting chat messages: {str(e)}")
            return json.dumps({"error": str(e)})

    def get_all_messages(self) -> str:
        """Get messages from all available chats"""
        try:
            # First get all chats
            chats = self.client.get_chats()
            all_messages = []
            
            # Then get messages from each chat
            for chat in chats:
                chat_id = chat.get('id')
                if chat_id:
                    messages = self.client.get_messages_as_list(chat_id)
                    # Add chat info to each message for context
                    for message in messages:
                        message['chat_info'] = {
                            'id': chat.get('id'),
                            'name': chat.get('name'),
                            'account_type': chat.get('account_type'),
                            'account_id': chat.get('account_id')
                        }
                    all_messages.extend(messages)
            
            return json.dumps(all_messages, default=str)
        except Exception as e:
            logger.error(f"Error getting all messages: {str(e)}")
            return json.dumps({"error": str(e)})

async def main(dsn: Optional[str] = None, api_key: Optional[str] = None):
    """Run the Unipile MCP server."""
    logger.info("Server starting")
    unipile = UnipileWrapper(dsn, api_key)
    server = Server("unipile")

    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        return [
            types.Resource(
                uri=AnyUrl("unipile://accounts"),
                name="Unipile Accounts",
                description="List of connected messaging accounts including MOBILE, MAIL, WHATSAPP, LINKEDIN, SLACK, TWITTER, TELEGRAM, INSTAGRAM, MESSENGER, and more",
                mimeType="application/json",
            ),
            types.Resource(
                uri=AnyUrl("unipile://chats"),
                name="Unipile Chats",
                description="List of available chats across all connected accounts, including details like account type, chat name, unread count, and platform-specific features. Supported account types: Mobile, Mail, Google, ICloud, Outlook, Google Calendar, Whatsapp, Linkedin, Slack, Twitter, Exchange, Telegram, Instagram, Messenger.",
                mimeType="application/json",
            ),
            types.Resource(
                uri=AnyUrl("unipile://messages"),
                name="Unipile Messages",
                description="Messages from connected messaging platforms, including text content, attachments (images, videos, audio, files), reactions, quoted messages, and message metadata. Supported account types: Mobile, Mail, Google, ICloud, Outlook, Google Calendar, Whatsapp, Linkedin, Slack, Twitter, Exchange, Telegram, Instagram, Messenger.",
                mimeType="application/json",
            )
        ]

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        if uri.scheme != "unipile":
            raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

        path = str(uri).replace("unipile://", "")
        try:
            if path == "accounts":
                return unipile.get_accounts()
            elif path == "chats":
                return unipile.get_chats()
            elif path == "messages":
                return unipile.get_all_messages()
            else:
                raise ValueError(f"Unknown resource path: {path}")
        except Exception as e:
            logger.error(f"Error reading resource {path}: {str(e)}")
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}),
                mimeType="application/json",
                uri=uri
            )]

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available tools"""
        return [
            types.Tool(
                name="unipile_get_accounts",
                description="Get all connected messaging accounts. Returns account details including type (MOBILE, MAIL, WHATSAPP, etc.), connection parameters, ID, name, creation date, signatures, groups, and sources.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="unipile_get_chats",
                description="Get all available chats. Returns chat details including ID, account type (WHATSAPP, LINKEDIN, etc.), name, unread count, archived status, and platform-specific features like folder location for email or organization details for LinkedIn.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="unipile_get_chat_messages",
                description="Get all messages from a Unipile chat. Returns message details including text content, sender info, timestamps, attachments (images, videos, audio, files), reactions, quoted messages (replies), delivery status, and message metadata.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat_id": {"type": "string", "description": "The ID of the chat to get messages from"},
                        "batch_size": {"type": "integer", "description": "Number of messages to fetch per request (default: 100)"}
                    },
                    "required": ["chat_id"]
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict[str, Any] | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution requests"""
        try:
            if name == "unipile_get_accounts":
                results = unipile.get_accounts()
                logger.info(f"MCP response for tool {name}: {results}")
                return [types.TextContent(
                    type="text",
                    text=results,
                    mimeType="application/json",
                    uri=AnyUrl("unipile://accounts")
                )]
            elif name == "unipile_get_chats":
                results = unipile.get_chats()
                return [types.TextContent(
                    type="text",
                    text=results,
                    mimeType="application/json",
                    uri=AnyUrl("unipile://chats")
                )]
            elif name == "unipile_get_chat_messages":
                if not arguments:
                    raise ValueError("Missing arguments for get_chat_messages")
                
                chat_id = arguments["chat_id"]
                batch_size = arguments.get("batch_size", 100)
                
                results = unipile.get_chat_messages(chat_id, batch_size)
                return [types.TextContent(
                    type="text",
                    text=results,
                    mimeType="application/json",
                    uri=AnyUrl(f"unipile://messages/{chat_id}")
                )]
            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}),
                mimeType="application/json",
                uri=AnyUrl("unipile://error")
            )]

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Server running with stdio transport")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="unipile",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 