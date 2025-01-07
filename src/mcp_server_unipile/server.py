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

    def _extract_person_info(self, original_data: dict) -> dict:
        """Extract core person information from message data"""
        try:
            person_info = {}
            if "conversation" in original_data:
                participants = original_data["conversation"].get("conversationParticipants", [])
                for participant in participants:
                    if "participantType" in participant and "member" in participant["participantType"]:
                        member = participant["participantType"]["member"]
                        if member.get("firstName") and isinstance(member["firstName"], dict):
                            first_name = member["firstName"].get("text", "")
                            last_name = member["lastName"].get("text", "") if member.get("lastName") else ""
                            headline = member.get("headline", {}).get("text", "") if member.get("headline") else ""
                            pronoun = member.get("pronoun", {}).get("standardizedPronoun", "") if member.get("pronoun") else ""
                            
                            person_info[participant["backendUrn"]] = {
                                "name": f"{first_name} {last_name}".strip(),
                                "headline": headline,
                                "pronoun": pronoun
                            }
            return person_info
        except Exception as e:
            logger.error(f"Error extracting person info: {str(e)}")
            return {}

    def _extract_core_message(self, message: dict) -> dict:
        """Extract core message content and metadata"""
        try:
            # Extract basic message info
            core_message = {
                "id": message.get("id", ""),
                "text": message.get("text", ""),
                "timestamp": message.get("timestamp", ""),
                "sender_id": message.get("sender_id", ""),
                "chat_info": message.get("chat_info", {})
            }

            # Extract person information if original data exists
            if "original" in message:
                try:
                    original_data = json.loads(message["original"])
                    person_info = self._extract_person_info(original_data)
                    if person_info:
                        core_message["participants"] = person_info
                except json.JSONDecodeError:
                    pass

            return core_message
        except Exception as e:
            logger.error(f"Error extracting core message: {str(e)}")
            return message

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

    def get_chats(self, account_id: str, limit: int = 10) -> str:
        """Get all available chats for a specific account"""
        try:
            # The account_id may be looks like this: abcdefg_MESSAGING
            # remove the _MESSAGING part
            account_id = account_id.replace("_MESSAGING", "")
            chats = self.client.get_chats(account_id=account_id, limit=limit)
            return json.dumps(chats)
        except Exception as e:
            logger.error(f"Error getting chats: {str(e)}")
            return json.dumps({"error": str(e)})

    def get_chat_messages(self, chat_id: str, batch_size: int = 100) -> str:
        """Get all messages from a chat"""
        try:
            messages = self.client.get_messages_as_list(chat_id, batch_size)
            # Transform each message to extract core content
            core_messages = [self._extract_core_message(msg) for msg in messages]
            return json.dumps(core_messages)
        except Exception as e:
            logger.error(f"Error getting chat messages: {str(e)}")
            return json.dumps({"error": str(e)})

    def get_all_messages(self, account_id: str, limit: int = 10) -> str:
        """Get messages from all available chats for a specific account"""
        try:
            # First get all chats for this account
            chats = json.loads(self.get_chats(account_id, limit))
            if isinstance(chats, dict) and "error" in chats:
                return json.dumps(chats)
                
            all_messages = []
            
            # Then get messages from each chat
            for chat in chats:
                chat_id = chat.get('id')
                if chat_id:
                    messages = self.client.get_messages_as_list(chat_id)
                    # Transform each message to extract core content
                    core_messages = [self._extract_core_message(msg) for msg in messages]
                    all_messages.extend(core_messages)
            
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
                description="List of connected messaging accounts from supported platforms: Mobile, Mail, WhatsApp, LinkedIn, Slack, Twitter, Telegram, Instagram, Messenger",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        if uri.scheme != "unipile":
            raise ValueError(f"Unsupported URI scheme: {uri.scheme}")

        path = str(uri).replace("unipile://", "")
        try:
            if path == "accounts":
                return unipile.get_accounts()
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
                description="Get all connected messaging accounts from supported platforms: Mobile, Mail, WhatsApp, LinkedIn, Slack, Twitter, Telegram, Instagram, Messenger. Returns account details including connection parameters, ID, name, creation date, signatures, groups, and sources.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="unipile_get_recent_messages",
                description="Get recent messages from all chats associated with a specific account. Supports messages from: Mobile, Mail, WhatsApp, LinkedIn, Slack, Twitter, Telegram, Instagram, Messenger. Returns message details including text content, sender info, timestamps, attachments, reactions, quoted messages, and metadata.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string", "description": "The one source ID of of the account to get messages from. It is the id of the source objects in the account's sources array."},
                        "batch_size": {"type": "integer", "description": "Number of messages to fetch per chat (default: 20)"}
                    },
                    "required": ["account_id"]
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
            elif name == "unipile_get_recent_messages":
                if not arguments:
                    raise ValueError("Missing arguments for get_recent_messages")
                
                account_id = arguments["account_id"]
                batch_size = arguments.get("batch_size", 10)
                
                # Get all chats first
                chats = json.loads(unipile.get_chats(account_id=account_id, limit=batch_size))
                if isinstance(chats, dict) and "error" in chats:
                    return [types.TextContent(
                        type="text",
                        text=json.dumps(chats),
                        mimeType="application/json",
                        uri=AnyUrl(f"unipile://error")
                    )]
                    
                all_messages = []
                for chat in chats:
                    chat_id = chat.get('id')
                    if chat_id:
                        messages = json.loads(unipile.get_chat_messages(chat_id, batch_size))
                        if isinstance(messages, list):
                            for message in messages:
                                message['chat_info'] = {
                                    'id': chat.get('id'),
                                    'name': chat.get('name'),
                                    'account_type': chat.get('account_type'),
                                    'account_id': chat.get('account_id')
                                }
                            all_messages.extend(messages)
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(all_messages, default=str),
                    mimeType="application/json",
                    uri=AnyUrl(f"unipile://messages/{account_id}")
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