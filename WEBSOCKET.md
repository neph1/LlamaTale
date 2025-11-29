# WebSocket Support for LlamaTale Web Interface

## Overview

LlamaTale uses WebSocket connections for the web browser interface in both single-player (IF) mode and multi-player (MUD) mode, providing a modern bidirectional communication channel between the client and server.

## Features

- **Bidirectional Communication**: WebSocket enables real-time, two-way communication between the browser and server
- **Reduced Latency**: Direct WebSocket communication is faster than HTTP polling or EventSource
- **Modern Stack**: Uses FastAPI and uvicorn for a modern, async Python web framework
- **Unified Approach**: Both IF and MUD modes now use the same WebSocket-based architecture

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

### Starting a Single-Player Game

```bash
python -m tale.main --game stories/dungeon --web
```

### Starting a Multi-Player (MUD) Game

```bash
python -m tale.main --game stories/dungeon --mode mud
```

## Architecture

### Server-Side

The WebSocket implementation uses FastAPI and includes:

- **TaleFastAPIApp** (IF mode): FastAPI application for single-player with WebSocket endpoint
- **TaleMudFastAPIApp** (MUD mode): FastAPI application for multi-player with session management
- **WebSocket Endpoint** (`/tale/ws`): Handles bidirectional communication
- **HTTP Routes**: Serves static files and HTML pages
- **Message Protocol**: JSON-based messages for commands and responses

### Client-Side

The JavaScript client (`script.js`) includes:

- **WebSocket Connection**: Connects to the WebSocket endpoint
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
   - `TaleFastAPIApp`: FastAPI application for single-player mode
   - `HttpIo`: I/O adapter for the FastAPI web server

2. **`tale/tio/mud_browser_io.py`**:
   - `TaleMudFastAPIApp`: FastAPI application for multi-player mode with session management
   - `MudHttpIo`: I/O adapter for multi-player browser interface

3. **`tale/driver_if.py`**:
   - `IFDriver`: Creates FastAPI server for IF web interface

4. **`tale/driver_mud.py`**:
   - `MudDriver`: Creates FastAPI server for MUD web interface

5. **`tale/web/script.js`**:
   - `connectWebSocket()`: Establishes WebSocket connection
   - `send_cmd()`: Sends commands via WebSocket

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

If FastAPI is not available, an error will be raised when starting with web interface. Install FastAPI:

```bash
pip install fastapi websockets uvicorn
```

## Future Enhancements

Possible improvements for the WebSocket implementation:

- Compression for large text outputs
- Reconnection handling with session persistence
- WebSocket authentication and security enhancements
- Performance metrics and monitoring
