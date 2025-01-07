# Unipile MCP Server

## Overview

A Model Context Protocol (MCP) server implementation that provides integration with Unipile messaging platform. This server enables AI models to interact with messages from various messaging platforms (LinkedIn, WhatsApp, Instagram, Messenger, Telegram) through a standardized interface.

For more information about the Model Context Protocol and how it works, see [Anthropic's MCP documentation](https://www.anthropic.com/news/model-context-protocol).

## Components

### Resources

The server exposes the following resources:

* `unipile://messages`: A dynamic resource that provides access to messages from connected messaging platforms

### Example Prompts

- Get all messages from a chat:
    ```
    Get all messages from chat ID "chat_123"
    ```

### Tools

The server offers several tools for accessing Unipile data:

#### Message Management Tools
* `unipile_get_chat_messages`
  * Retrieve all messages from a specific chat with pagination support
  * Input: chat_id (required), batch_size (optional, default: 100)
  * Returns: Array of message objects

## Setup

You'll need a Unipile DSN and API key. You can obtain these from your Unipile dashboard.

### Environment Variables
- `UNIPILE_DSN`: Your Unipile DSN (e.g. api8.unipile.com:13851)
- `UNIPILE_API_KEY`: Your Unipile API key

Note: Keep your API key secure and never commit it to version control.

### Docker Installation

You can either build the image locally or pull it from Docker Hub. The image is built for the Linux platform.

#### Supported Platforms
- Linux/amd64
- Linux/arm64
- Linux/arm/v7

#### Option 1: Pull from Docker Hub
```bash
docker pull buryhuang/mcp-unipile:latest
```

#### Option 2: Build Locally
```bash
docker build -t mcp-unipile .
```

Run the container:
```bash
docker run \
  -e UNIPILE_DSN=your_dsn_here \
  -e UNIPILE_API_KEY=your_api_key_here \
  buryhuang/mcp-unipile:latest
```

## Cross-Platform Publishing

To publish the Docker image for multiple platforms, you can use the `docker buildx` command. Follow these steps:

1. **Create a new builder instance** (if you haven't already):
   ```bash
   docker buildx create --use
   ```

2. **Build and push the image for multiple platforms**:
   ```bash
   docker buildx build --platform linux/amd64,linux/arm64,linux/arm/v7 -t buryhuang/mcp-unipile:latest --push .
   ```

3. **Verify the image is available for the specified platforms**:
   ```bash
   docker buildx imagetools inspect buryhuang/mcp-unipile:latest
   ```

## Usage with Claude Desktop

### Docker Usage
```json
{
  "mcpServers": {
    "unipile": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "UNIPILE_DSN=your_dsn_here",
        "-e",
        "UNIPILE_API_KEY=your_api_key_here",
        "buryhuang/mcp-unipile:latest"
      ]
    }
  }
}
```

## Development

To set up the development environment:

```bash
pip install -e .
```

## License

This project is licensed under the MIT License. 
