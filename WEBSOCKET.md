# WebSocket Support for LlamaTale Web Interface

## Overview

LlamaTale now supports WebSocket connections for the web browser interface, providing a modern bidirectional communication channel between the client and server. This is an alternative to the traditional Server-Sent Events (EventSource) approach.

## Features

- **Bidirectional Communication**: WebSocket enables real-time, two-way communication between the browser and server
- **Reduced Latency**: Direct WebSocket communication can be faster than HTTP polling or EventSource
- **Modern Stack**: Uses FastAPI and uvicorn for a modern, async Python web framework
- **Backward Compatibility**: The JavaScript client automatically falls back to EventSource if WebSocket is not available

## Requirements

Install the additional dependencies:

```bash
pip install fastapi websockets uvicorn
```

Or install all requirements including WebSocket support:

```bash
pip install -r requirements.txt
```

## Usage

### Starting a Game with WebSocket Support

To enable WebSocket mode, use the `--websocket` flag when starting a game with the web interface:

```bash
python -m tale.main --game stories/dungeon --web --websocket
```

### Command-Line Arguments

- `--web`: Enable web browser interface
- `--websocket`: Use WebSocket instead of EventSource (requires `--web`)

### Example Commands

**Standard EventSource mode (default):**
```bash
python -m tale.main --game stories/dungeon --web
```

**WebSocket mode:**
```bash
python -m tale.main --game stories/dungeon --web --websocket
```

## Architecture

### Server-Side

The WebSocket implementation uses FastAPI and includes:

- **TaleFastAPIApp**: Main FastAPI application with WebSocket endpoint
- **WebSocket Endpoint** (`/tale/ws`): Handles bidirectional communication
- **HTTP Routes**: Serves static files and HTML pages
- **Message Protocol**: JSON-based messages for commands and responses

### Client-Side

The JavaScript client (`script.js`) includes:

- **Automatic Detection**: Tries WebSocket first, falls back to EventSource
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
   - `HttpIo`: Updated to support both WSGI and FastAPI modes

2. **`tale/driver_if.py`**:
   - `IFDriver`: Updated constructor with `use_websocket` parameter
   - `connect_player()`: Creates FastAPI server when WebSocket mode is enabled

3. **`tale/web/script.js`**:
   - `tryWebSocket()`: Attempts WebSocket connection
   - `setupEventSource()`: Fallback to EventSource
   - `send_cmd()`: Sends commands via WebSocket or AJAX

4. **`tale/main.py`**:
   - Added `--websocket` command-line argument

### Limitations

- WebSocket mode is currently only supported in single-player (IF) mode
- SSL/TLS configuration may require additional setup for WebSocket secure connections
- The implementation maintains backward compatibility with the original WSGI-based approach

## Troubleshooting

### WebSocket Connection Fails

If the WebSocket connection fails, the client will automatically fall back to EventSource. Check:

1. FastAPI and uvicorn are installed
2. Port is not blocked by firewall
3. Browser console for error messages

### Module Not Found Errors

Ensure all dependencies are installed:

```bash
pip install -r requirements.txt
```

### ImportError for FastAPI

If FastAPI is not available, the system will fall back to the traditional WSGI server. Install FastAPI to enable WebSocket support:

```bash
pip install fastapi websockets uvicorn
```

## Future Enhancements

Possible improvements for the WebSocket implementation:

- Multi-player (MUD) mode support
- Compression for large text outputs
- Reconnection handling with session persistence
- WebSocket authentication and security enhancements
- Performance metrics and monitoring
