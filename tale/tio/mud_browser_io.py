"""
Webbrowser based I/O for a multi player ('mud') server.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import hashlib
import json
import random
import sys
import time
import asyncio
from html import escape as html_escape
from threading import Lock
from typing import Dict, Any, List, Tuple, Optional

from .. import vfs
from .if_browser_io import HttpIo
from .. import __version__ as tale_version_str
from ..driver import Driver
from ..player import PlayerConnection

# Import FastAPI dependencies
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, Response
import uvicorn

__all__ = ["MudHttpIo", "TaleMudFastAPIApp"]


class MudHttpIo(HttpIo):
    """
    I/O adapter for a http/browser based interface for MUD mode.
    """
    def __init__(self, player_connection: PlayerConnection) -> None:
        super().__init__(player_connection, None)
        self.supports_blocking_input = False
        self.dont_echo_next_cmd = False   # used to cloak password input

    def singleplayer_mainloop(self, player_connection: PlayerConnection) -> None:
        raise RuntimeError("this I/O adapter is for multiplayer (mud) mode")

    def pause(self, unpause: bool=False) -> None:
        # we'll never pause a mud server.
        pass


class SessionManager:
    """Manages player sessions for multi-player mode."""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
    
    def generate_id(self) -> str:
        string = "%d%d%f" % (random.randint(0, sys.maxsize), id(self), time.time())
        return hashlib.sha1(string.encode("ascii")).hexdigest()
    
    def create_session(self) -> Tuple[str, Dict[str, Any]]:
        sid = self.generate_id()
        session = {
            "id": sid,
            "created": time.time(),
            "player_connection": None
        }
        with self._lock:
            self.sessions[sid] = session
        return sid, session
    
    def get_session(self, sid: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.sessions.get(sid)
    
    def delete_session(self, sid: str) -> None:
        with self._lock:
            if sid in self.sessions:
                del self.sessions[sid]


class TaleMudFastAPIApp:
    """
    FastAPI-based application with WebSocket support for multi-player (MUD) mode.
    This handles multiple connected clients with session management.
    """
    def __init__(self, driver: Driver, use_ssl: bool=False, 
                 ssl_certs: Tuple[str, str, str]=None) -> None:
        self.driver = driver
        self.use_ssl = use_ssl
        self.ssl_certs = ssl_certs
        self.session_manager = SessionManager()
        self.app = FastAPI()
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Setup all FastAPI routes"""
        
        @self.app.get("/")
        async def root():
            return RedirectResponse(url="/tale/")
        
        @self.app.get("/tale/")
        @self.app.get("/tale/start")
        async def start_page():
            resource = vfs.internal_resources["web/index.html"]
            txt = resource.text.format(
                story_version=self.driver.story.config.version,
                story_name=self.driver.story.config.name,
                story_author=self.driver.story.config.author,
                story_author_email=self.driver.story.config.author_address
            )
            return HTMLResponse(content=txt)
        
        @self.app.get("/tale/story")
        async def story_page():
            resource = vfs.internal_resources["web/story.html"]
            txt = resource.text.format(
                story_version=self.driver.story.config.version,
                story_name=self.driver.story.config.name,
                story_author=self.driver.story.config.author,
                story_author_email=self.driver.story.config.author_address
            )
            # For MUD mode, don't show save button
            txt = txt.replace('<input type="button" id="saveButton" value="Save story" onclick="showSaveDialog()" readonly/>', '')
            return HTMLResponse(content=txt)
        
        @self.app.get("/tale/about")
        async def about_page():
            resource = vfs.internal_resources["web/about_mud.html"]
            player_table = []
            for name, conn in self.driver.all_players.items():
                player_table.append(html_escape("Name:  %s   connection: %s" % (name, conn.io)))
            player_table.append("</pre>")
            player_table_txt = "\n".join(player_table)
            txt = resource.text.format(
                tale_version=tale_version_str,
                story_version=self.driver.story.config.version,
                story_name=self.driver.story.config.name,
                uptime="%d:%02d:%02d" % self.driver.uptime,
                starttime=self.driver.server_started,
                num_players=len(self.driver.all_players),
                player_table=player_table_txt
            )
            return HTMLResponse(content=txt)
        
        @self.app.get("/tale/quit")
        async def quit_page():
            # In MUD mode, we just end this player's session
            return HTMLResponse(
                content="<html><body><script>window.close();</script>"
                "<p><strong>Tale game session ended.</strong></p>"
                "<p>You may close this window/tab.</p></body></html>"
            )
        
        @self.app.get("/tale/static/{file_path:path}")
        async def serve_static(file_path: str):
            """Serve static files"""
            try:
                resource = vfs.internal_resources["web/" + file_path]
                if resource.is_text:
                    return HTMLResponse(content=resource.text)
                else:
                    return Response(content=resource.data, media_type=resource.mimetype)
            except KeyError:
                from fastapi import HTTPException
                raise HTTPException(status_code=404, detail="File not found")
        
        @self.app.websocket("/tale/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            
            # Create a new session and player connection for this WebSocket
            sid, session = self.session_manager.create_session()
            
            # Create player connection
            conn = self.driver.connect_player("web", 0)
            session["player_connection"] = conn
            
            # Send initial connected message
            await websocket.send_text(json.dumps({"type": "connected"}))
            
            try:
                while self.driver.is_running():
                    # Check for server output first
                    has_output = False
                    if conn.io and conn.player:
                        # Check for HTML output
                        html = conn.io.get_html_to_browser()
                        special = conn.io.get_html_special()
                        data_items = conn.io.get_data_to_browser()
                        
                        if html or special:
                            location = conn.player.location
                            if conn.io.dont_echo_next_cmd:
                                special.append("noecho")
                            npc_names = ''
                            items = ''
                            exits = ''
                            if location:
                                npc_names = ','.join([l.name for l in location.livings if l.alive and l.visible and l != conn.player])
                                items = ','.join([i.name for i in location.items if i.visible])
                                exits = ','.join(list(set([e.name for e in location.exits.values() if e.visible])))
                            
                            response = {
                                "type": "text",
                                "text": "\n".join(html),
                                "special": special,
                                "turns": conn.player.turns,
                                "location": location.title if location else "???",
                                "location_image": location.avatar if location and location.avatar else "",
                                "npcs": npc_names if location else '',
                                "items": items if location else '',
                                "exits": exits if location else '',
                            }
                            await websocket.send_text(json.dumps(response))
                            has_output = True
                        elif data_items:
                            for d in data_items:
                                response = {"type": "data", "data": d}
                                await websocket.send_text(json.dumps(response))
                            has_output = True
                    else:
                        break
                    
                    # Handle player input with adaptive timeout
                    timeout = 0.1 if has_output else 0.5
                    try:
                        data = await asyncio.wait_for(websocket.receive_text(), timeout=timeout)
                        self._handle_player_input(conn, data)
                    except asyncio.TimeoutError:
                        # No input received, continue loop
                        if not has_output:
                            await asyncio.sleep(0.1)
                        
            except WebSocketDisconnect:
                print(f"WebSocket disconnected for player {conn.player.name if conn and conn.player else 'unknown'}")
                self._cleanup_player(conn, sid)
            except asyncio.CancelledError:
                print(f"WebSocket task cancelled for player {conn.player.name if conn and conn.player else 'unknown'}")
                self._cleanup_player(conn, sid)
                raise
            except Exception as e:
                import traceback
                print(f"WebSocket error for player {conn.player.name if conn and conn.player else 'unknown'}: {e}")
                print(traceback.format_exc())
                self._cleanup_player(conn, sid)
    
    def _handle_player_input(self, conn: PlayerConnection, data: str) -> None:
        """Handle player input from WebSocket"""
        try:
            message = json.loads(data)
            cmd = message.get("cmd", "")
            
            if "autocomplete" in message:
                # Handle autocomplete
                if cmd:
                    suggestions = conn.io.tab_complete(cmd, self.driver)
                    if suggestions:
                        conn.io.append_html_to_browser("<br><p><em>Suggestions:</em></p>")
                        conn.io.append_html_to_browser("<p class='txt-monospaced'>" + " &nbsp; ".join(suggestions) + "</p>")
                    else:
                        conn.io.append_html_to_browser("<p>No matching commands.</p>")
            else:
                # Normal command processing
                self._process_command(conn, cmd)
        except json.JSONDecodeError:
            # Handle plain text input
            self._process_command(conn, data)
    
    def _process_command(self, conn: PlayerConnection, cmd: str) -> None:
        """Process a command from the player"""
        cmd = html_escape(cmd, False)
        if cmd:
            if conn.io.dont_echo_next_cmd:
                conn.io.dont_echo_next_cmd = False
            elif conn.io.echo_input:
                conn.io.append_html_to_browser("<span class='txt-userinput'>%s</span>" % cmd)
        conn.player.store_input_line(cmd)
    
    def _cleanup_player(self, conn: PlayerConnection, sid: str) -> None:
        """Cleanup when player disconnects"""
        if conn and conn.player:
            self.driver.disconnect_player(conn)
        self.session_manager.delete_session(sid)
    
    @classmethod
    def create_app_server(cls, driver: Driver, *,
                          use_ssl: bool=False, ssl_certs: Tuple[str, str, str]=None):
        """Create and return a FastAPI app instance"""
        instance = cls(driver, use_ssl, ssl_certs)
        return instance
    
    def run(self, host: str, port: int) -> None:
        """Run the FastAPI server"""
        config = uvicorn.Config(
            self.app,
            host=host,
            port=port,
            log_level="warning"
        )
        if self.use_ssl and self.ssl_certs:
            config.ssl_certfile = self.ssl_certs[0]
            config.ssl_keyfile = self.ssl_certs[1]
        
        server = uvicorn.Server(config)
        server.run()
