import requests
import logging
from typing import List, Dict, Optional, Generator

logger = logging.getLogger(__name__)

class UnipileClient:
    def __init__(self, dsn: str, api_key: str):
        """
        Initialize the Unipile client
        
        Args:
            dsn: Your Unipile DSN (e.g. 'api8.unipile.com:13851')
            api_key: Your Unipile API key
        """
        self.base_url = f"https://{dsn}"
        self.headers = {
            'X-API-KEY': api_key,
            'accept': 'application/json'
        }

    def get_accounts(self) -> List[Dict]:
        """
        Get all connected accounts
        
        Returns:
            List of account dictionaries from the items array
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        url = f"{self.base_url}/api/v1/accounts"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        
        # The accounts are in the items array
        if data.get("object") == "AccountList":
            return data.get("items", [])
        return []

    def get_chats(self, account_id: str, limit: int = 10) -> List[Dict]:
        """
        Get available chats for a specific account
        
        Args:
            account_id: The ID of the account to get chats from
            limit: Maximum number of chats to return (default: 10)
        
        Returns:
            List of chat dictionaries from the items array. Each chat contains:
            - id: The chat ID
            - account_id: The associated account ID
            - account_type: The type of account (e.g., WHATSAPP, LINKEDIN)
            - provider_id: The provider's chat ID
            - name: Chat name or title
            - type: Chat type
            - timestamp: Last activity timestamp
            - unread_count: Number of unread messages
            - archived: Whether the chat is archived
            - subject: Chat subject or topic
            And more platform-specific fields
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        url = f"{self.base_url}/api/v1/chats?account_id={account_id}&limit={limit}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        
        # The chats are in the items array
        if data.get("object") == "ChatList":
            return data.get("items", [])
        return []

    def get_all_messages(self, chat_id: str, batch_size: int = 100) -> Generator[Dict, None, None]:
        """
        Get all messages from a chat using pagination
        
        Args:
            chat_id: The ID of the chat to get messages from
            batch_size: Number of messages to fetch per request (default: 100)
            
        Returns:
            Generator yielding message dictionaries. Each message contains:
            - id: Message ID
            - provider_id: Provider's message ID
            - sender_id: ID of the message sender
            - text: Message text content
            - attachments: List of attachments (images, videos, audio, files)
            - chat_id: ID of the chat
            - timestamp: Message timestamp
            - is_sender: Whether the current user is the sender
            - reactions: List of reactions to the message
            - quoted: Quoted message details (if this is a reply)
            And more message metadata
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        cursor = None
        
        while True:
            # Prepare URL and parameters
            url = f"{self.base_url}/api/v1/chats/{chat_id}/messages"
            params = {'limit': batch_size}
            if cursor:
                params['cursor'] = cursor
                
            # Make API request
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # The messages are in the items array
            if data.get("object") == "MessageList":
                messages = data.get("items", [])
                # Yield each message
                for message in messages:
                    yield message
                
                # Get cursor for next page
                cursor = data.get('cursor')
                
                # If no cursor or cursor is null, we've reached the end
                if not cursor:
                    break
            else:
                break

    def get_messages_as_list(self, chat_id: str, batch_size: int = 100) -> List[Dict]:
        """
        Get all messages from a chat as a list
        
        Args:
            chat_id: The ID of the chat to get messages from
            batch_size: Number of messages to fetch per request (default: 100)
            
        Returns:
            List of message dictionaries
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        return list(self.get_all_messages(chat_id, batch_size))

    def get_emails(self, account_id: str, limit: int = 10) -> List[Dict]:
        """
        Get emails for a specific account
        
        Args:
            account_id: The ID of the account to get emails from
            limit: Maximum number of emails to return (default: 10)
            
        Returns:
            List of email dictionaries from the items array. Each email contains:
            - id: Email ID
            - account_id: The associated account ID
            - type: Email type (MAIL)
            - date: Email timestamp
            - role: Email role (inbox, sent, etc.)
            - folders: List of folder names
            - subject: Email subject
            - body: Email body (HTML)
            - body_plain: Email body (plain text)
            - from_attendee: Sender information
            - to_attendees: Recipients information
            - attachments: List of attachments
            And more email metadata
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        url = f"{self.base_url}/api/v1/emails"
        params = {
            'account_id': account_id,
            'limit': limit
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        # The emails are in the items array
        if data.get("object") == "EmailList":
            return data.get("items", [])
        return []

# Example usage:
if __name__ == "__main__":
    # Initialize client
    client = UnipileClient(
        dsn="api8.unipile.com:13851",  # Replace with your DSN
        api_key="your_access_token_here"     # Replace with your access token
    )
    
    # Get messages using generator (memory efficient for large chats)
    chat_id = "your_chat_id"
    for message in client.get_all_messages(chat_id):
        print(f"Message: {message}")
        