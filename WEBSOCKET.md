# WebSocket Support for LlamaTale Web Interface

## Overview

LlamaTale uses WebSocket connections for the web browser interface in single-player (IF) mode, providing a modern bidirectional communication channel between the client and server. This replaces the older Server-Sent Events (EventSource) approach for IF mode.

**Note**: Multi-player (MUD) mode still uses the EventSource/WSGI-based implementation.

## Features

- **Bidirectional Communication**: WebSocket enables real-time, two-way communication between the browser and server
- **Reduced Latency**: Direct WebSocket communication is faster than HTTP polling or EventSource
- **Modern Stack**: Uses FastAPI and uvicorn for a modern, async Python web framework

## Requirements

Install the required dependencies:

```bash
pip install fastapi websockets uvicorn
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## Usage

### Starting a Game with Web Interface

To start a game with the web interface (uses WebSocket automatically):

```bash
python -m tale.main --game stories/dungeon --web
```

### Command-Line Arguments

- `--web`: Enable web browser interface (uses WebSocket for IF mode)

## Architecture

### Server-Side

The WebSocket implementation uses FastAPI and includes:

- **TaleFastAPIApp**: Main FastAPI application with WebSocket endpoint
- **WebSocket Endpoint** (`/tale/ws`): Handles bidirectional communication
- **HTTP Routes**: Serves static files and HTML pages
- **Message Protocol**: JSON-based messages for commands and responses

### Client-Side

The JavaScript client (`script.js`) includes:

- **WebSocket Connection**: Connects to the WebSocket endpoint
- **EventSource Fallback**: Falls back to EventSource for MUD mode
- **Message Handling**: Processes incoming text, data, and status messages
- **Command Sending**: Sends commands and autocomplete requests via WebSocket

### Message Format

**Client to Server:**
```json
{
  "cmd": "look around",
  "autocomplete": 0
}
```

**Server to Client (text):**
```json
{
  "type": "text",
  "text": "<p>You see a dark corridor...</p>",
  "special": [],
  "turns": 42,
  "location": "Dark Corridor",
  "location_image": "",
  "npcs": "goblin,troll",
  "items": "sword,potion",
  "exits": "north,south"
}
```

**Server to Client (data):**
```json
{
  "type": "data",
  "data": "base64_encoded_image..."
}
```

## Implementation Details

### Key Components

1. **`tale/tio/if_browser_io.py`**:
   - `TaleFastAPIApp`: FastAPI application with WebSocket support
   - `HttpIo`: I/O adapter for the FastAPI web server

2. **`tale/driver_if.py`**:
   - `IFDriver`: Creates FastAPI server for web interface
   - `connect_player()`: Initializes the HttpIo with the FastAPI server

3. **`tale/web/script.js`**:
   - `tryWebSocket()`: Attempts WebSocket connection
   - `setupEventSource()`: Fallback for MUD mode
   - `send_cmd()`: Sends commands via WebSocket or AJAX

### Multi-Player Mode

Multi-player (MUD) mode still uses the traditional EventSource/WSGI implementation in `tale/tio/mud_browser_io.py`. The frontend JavaScript automatically falls back to EventSource when WebSocket is not available.

## Troubleshooting

### WebSocket Connection Fails

If the WebSocket connection fails:

1. Ensure FastAPI and uvicorn are installed
2. Check that the port is not blocked by firewall
3. Check browser console for error messages

### Module Not Found Errors

Ensure all dependencies are installed:

```bash
pip install fastapi websockets uvicorn
```

### ImportError for FastAPI

If FastAPI is not available, an error will be raised when starting IF mode with web interface. Install FastAPI:

```bash
pip install fastapi websockets uvicorn
```

## Future Enhancements

Possible improvements for the WebSocket implementation:

- Multi-player (MUD) mode WebSocket support
- Compression for large text outputs
- Reconnection handling with session persistence
- WebSocket authentication and security enhancements
- Performance metrics and monitoring
