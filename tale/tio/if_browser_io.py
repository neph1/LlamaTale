"""
Webbrowser based I/O for a single player ('if') story.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import json
import time
import asyncio
from html import escape as html_escape
from threading import Lock, Event, Thread
from typing import Sequence, Tuple, Any, Optional, Dict, List

from tale.web.web_utils import create_chat_container, dialogue_splitter

from . import iobase
from .. import mud_context, vfs, lang
from .styleaware_wrapper import tag_split_re
from .. import __version__ as tale_version_str
from ..driver import Driver
from ..player import PlayerConnection

__all__ = ["HttpIo", "TaleFastAPIApp"]

# Try to import FastAPI-related dependencies
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, Response
    from fastapi.staticfiles import StaticFiles
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


style_tags_html = {
    "<dim>": ("<span class='txt-dim'>", "</span>"),
    "<normal>": ("<span class='txt-normal'>", "</span>"),
    "<bright>": ("<span class='txt-bright'>", "</span>"),
    "<ul>": ("<span class='txt-ul'>", "</span>"),
    "<it>": ("<span class='txt-it'>", "</span>"),
    "<rev>": ("<span class='txt-rev'>", "</span>"),
    "</>": None,
    "<clear>": None,
    "<location>": ("<span class='txt-location'>", "</span>"),
    "<monospaced>": ("<span class='txt-monospaced'>", "</span>")
}


class HttpIo(iobase.IoAdapterBase):
    """
    I/O adapter for a http/browser based interface.
    This runs as a web server using FastAPI with WebSocket support.
    This way it is a simple call for the driver, it starts everything that is needed.
    """
    def __init__(self, player_connection: PlayerConnection, server: Any) -> None:
        super().__init__(player_connection)
        self.fastapi_server = server  # Reference to FastAPI app instance
        self.__html_to_browser = []    # type: List[str]   # the lines that need to be displayed in the player's browser
        self.__html_special = []       # type: List[str]   # special out of band commands (such as 'clear')
        self.__html_to_browser_lock = Lock()
        self.__new_html_available = Event()
        self.__data_to_browser = []

    def destroy(self) -> None:
        self.__new_html_available.set()

    def append_html_to_browser(self, text: str) -> None:
        with self.__html_to_browser_lock:
            self.__html_to_browser.append(text)
            self.__new_html_available.set()

    def append_html_special(self, text: str) -> None:
        with self.__html_to_browser_lock:
            self.__html_special.append(text)
            self.__new_html_available.set()

    def append_data_to_browser(self, data: str) -> None:
        with self.__html_to_browser_lock:
            self.__data_to_browser.append(data)
            self.__new_html_available.set()

    def get_html_to_browser(self) -> List[str]:
        with self.__html_to_browser_lock:
            html, self.__html_to_browser = self.__html_to_browser, []
            return html

    def get_html_special(self) -> List[str]:
        with self.__html_to_browser_lock:
            special, self.__html_special = self.__html_special, []
            return special
        
    def get_data_to_browser(self) -> List[str]:
        with self.__html_to_browser_lock:
            data, self.__data_to_browser = self.__data_to_browser, []
            return data

    def wait_html_available(self, timeout: float=None) -> None:
        self.__new_html_available.wait(timeout=timeout)
        self.__new_html_available.clear()

    def singleplayer_mainloop(self, player_connection: PlayerConnection) -> None:
        """mainloop for the web browser interface for single player mode using FastAPI/WebSocket"""
        import webbrowser
        from threading import Thread
        
        protocol = "https" if self.fastapi_server.use_ssl else "http"
        hostname = self.fastapi_server.driver.story.config.mud_host
        port = self.fastapi_server.driver.story.config.mud_port
        if hostname.startswith("127.0"):
            hostname = "localhost"
        url = "%s://%s:%d/tale/" % (protocol, hostname, port)
        print("Access the game on this web server url (WebSocket):  ", url, end="\n\n")
        
        t = Thread(target=webbrowser.open, args=(url, ))
        t.daemon = True
        t.start()
        
        # Run FastAPI server in the main thread
        try:
            self.fastapi_server.run(self.fastapi_server.driver.story.config.mud_host, 
                                  self.fastapi_server.driver.story.config.mud_port)
        except KeyboardInterrupt:
            print("* break - stopping server loop")
            if lang.yesno(input("Are you sure you want to exit the Tale driver, and kill the game? ")):
                pass
        print("Game shutting down.")

    def pause(self, unpause: bool=False) -> None:
        pass

    def clear_screen(self) -> None:
        self.append_html_special("clear")

    def render_output(self, paragraphs: Sequence[Tuple[str, bool]], **params: Any) -> str:
        if not paragraphs:
            return ""
        with self.__html_to_browser_lock:
            for text, formatted in paragraphs:
                text = self.convert_to_html(text)
                if text == "\n":
                    text = "<br>"
                if dialogue_splitter in text:
                    text = create_chat_container(text)
                    self.__html_to_browser.append("<p>" + text + "</p>\n")
                elif formatted:
                    self.__html_to_browser.append("<p>" + text + "</p>\n")
                else:
                    self.__html_to_browser.append("<pre>" + text + "</pre>\n")
            self.__new_html_available.set()
        return ""    # the output is pushed to the browser via a buffer, rather than printed to a screen

    def output(self, *lines: str) -> None:
        super().output(*lines)
        with self.__html_to_browser_lock:
            for line in lines:
                self.output_no_newline(line)
            self.__new_html_available.set()

    def output_no_newline(self, text: str, new_paragraph = True) -> None:
        super().output_no_newline(text, new_paragraph)
        text = self.convert_to_html(text)
        if text == "\n":
            text = "<br>"
        if new_paragraph:
            self.__html_to_browser.append("<p>" + text + "</p>\n")
        else:
            self.__html_to_browser.append(text.replace("\\n", "<br>"))
        self.__new_html_available.set()

    def convert_to_html(self, line: str) -> str:
        """Convert style tags to html"""
        chunks = tag_split_re.split(line)
        if len(chunks) == 1:
            # optimization in case there are no markup tags in the text at all
            return html_escape(self.smartquotes(line), False)
        result = []
        close_tags_stack = []
        chunks.append("</>")   # add a reset-all-styles sentinel
        for chunk in chunks:
            html_tags = style_tags_html.get(chunk)
            if html_tags:
                chunk = html_tags[0]
                close_tags_stack.append(html_tags[1])
            elif chunk == "</>":
                while close_tags_stack:
                    result.append(close_tags_stack.pop())
                continue
            elif chunk == "<clear>":
                self.append_html_special("clear")
            elif chunk:
                if chunk.startswith("</"):
                    chunk = "<" + chunk[2:]
                    html_tags = style_tags_html.get(chunk)
                    if html_tags:
                        chunk = html_tags[1]
                        if close_tags_stack:
                            close_tags_stack.pop()
                else:
                    # normal text (not a tag)
                    chunk = html_escape(self.smartquotes(chunk), False)
            result.append(chunk)
        return "".join(result)
    
    def send_data(self, data: str) -> None:
        self.append_data_to_browser(data)


if FASTAPI_AVAILABLE:
    class TaleFastAPIApp:
        """
        FastAPI-based application with WebSocket support for single player mode.
        This provides a modern WebSocket interface instead of Server-Sent Events.
        """
        def __init__(self, driver: Driver, player_connection: PlayerConnection,
                     use_ssl: bool=False, ssl_certs: Tuple[str, str, str]=None) -> None:
            self.driver = driver
            self.player_connection = player_connection
            self.use_ssl = use_ssl
            self.ssl_certs = ssl_certs
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
                txt = self._modify_web_page(self.player_connection, txt)
                return HTMLResponse(content=txt)
            
            @self.app.get("/tale/about")
            async def about_page():
                resource = vfs.internal_resources["web/about.html"]
                txt = resource.text.format(
                    tale_version=tale_version_str,
                    story_version=self.driver.story.config.version,
                    story_name=self.driver.story.config.name,
                    uptime="%d:%02d:%02d" % self.driver.uptime,
                    starttime=self.driver.server_started
                )
                return HTMLResponse(content=txt)
            
            @self.app.get("/tale/quit")
            async def quit_page():
                self.driver._stop_driver()
                return HTMLResponse(
                    content=b"<html><body><script>window.close();</script>"
                    b"<p><strong>Tale game session ended.</strong></p>"
                    b"<p>You may close this window/tab.</p></body></html>"
                )
            
            @self.app.get("/tale/static/{file_path:path}")
            async def serve_static(file_path: str):
                """Serve static files"""
                try:
                    resource = vfs.internal_resources["web/" + file_path]
                    if resource.is_text:
                        return HTMLResponse(content=resource.text)
                    else:
                        # For binary files, we need to return appropriate response
                        from fastapi.responses import Response
                        return Response(content=resource.data, media_type=resource.mimetype)
                except KeyError:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=404, detail="File not found")
            
            @self.app.websocket("/tale/ws")
            async def websocket_endpoint(websocket: WebSocket):
                await websocket.accept()
                
                # Get player from connection
                player = self._get_player_from_headers(websocket.headers)
                if not player or not player.io:
                    await websocket.close(code=1008, reason="Not logged in")
                    return
                
                # Send initial connected message
                await websocket.send_text(json.dumps({"type": "connected"}))
                
                try:
                    while self.driver.is_running():
                        # Check for server output first
                        has_output = False
                        if player.io:
                            # Check for HTML output
                            html = player.io.get_html_to_browser()
                            special = player.io.get_html_special()
                            data_items = player.io.get_data_to_browser()
                            
                            if html or special:
                                location = player.player.location
                                if player.io.dont_echo_next_cmd:
                                    special.append("noecho")
                                npc_names = ''
                                items = ''
                                exits = ''
                                if location:
                                    npc_names = ','.join([l.name for l in location.livings if l.alive and l.visible and l != player.player])
                                    items = ','.join([i.name for i in location.items if i.visible])
                                    exits = ','.join(list(set([e.name for e in location.exits.values() if e.visible])))
                                
                                response = {
                                    "type": "text",
                                    "text": "\n".join(html),
                                    "special": special,
                                    "turns": player.player.turns,
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
                        # Use shorter timeout if we just sent output (expecting response)
                        # Use longer timeout if idle (reduce CPU usage)
                        timeout = 0.1 if has_output else 0.5
                        try:
                            data = await asyncio.wait_for(websocket.receive_text(), timeout=timeout)
                            self._handle_player_input(player, data)
                        except asyncio.TimeoutError:
                            # No input received, continue loop
                            if not has_output:
                                # Nothing happened, wait a bit longer to reduce CPU usage
                                await asyncio.sleep(0.1)
                            
                except WebSocketDisconnect:
                    print(f"WebSocket disconnected for player {player.player.name if player and player.player else 'unknown'}")
                    self._cleanup_player(player)
                except asyncio.CancelledError:
                    # Task was cancelled, clean shutdown
                    print(f"WebSocket task cancelled for player {player.player.name if player and player.player else 'unknown'}")
                    self._cleanup_player(player)
                    raise
                except Exception as e:
                    # Log the error with context
                    import traceback
                    print(f"WebSocket error for player {player.player.name if player and player.player else 'unknown'}: {e}")
                    print(traceback.format_exc())
                    self._cleanup_player(player)
        
        def _get_player_from_headers(self, headers) -> Optional[PlayerConnection]:
            """Get player connection from WebSocket headers (similar to session)"""
            # For single player mode, we just return the single player connection
            return self.player_connection
        
        def _handle_player_input(self, conn: PlayerConnection, data: str) -> None:
            """Handle player input from WebSocket and feed into input queue"""
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
                # Handle plain text input for backward compatibility
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
        
        def _cleanup_player(self, conn: PlayerConnection) -> None:
            """Cleanup when player disconnects"""
            # In single player mode, disconnection means end of game
            if conn and conn.io:
                conn.io.destroy()
        
        def _modify_web_page(self, player_connection: PlayerConnection, html_content: str) -> str:
            """Modify the html before it is sent to the browser."""
            if not "wizard" in player_connection.player.privileges:
                html_content = html_content.replace('<label for="fileInput">Load character:</label>', '')
                html_content = html_content.replace('<input type="file" id="loadCharacterInput" accept=".json, .png, .jpeg, .jpg">', '')
            return html_content
        
        @classmethod
        def create_app_server(cls, driver: Driver, player_connection: PlayerConnection, *,
                              use_ssl: bool=False, ssl_certs: Tuple[str, str, str]=None):
            """Create and return a FastAPI app instance wrapped for server"""
            instance = cls(driver, player_connection, use_ssl, ssl_certs)
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
