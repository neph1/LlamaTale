"""
Webbrowser based I/O for a single player ('if') story.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import json
import time
import socket
import asyncio
from socketserver import ThreadingMixIn
from email.utils import formatdate, parsedate
from hashlib import md5
from html import escape as html_escape
from threading import Lock, Event, Thread
from typing import Iterable, Sequence, Tuple, Any, Optional, Dict, Callable, List
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer

from tale.web.web_utils import create_chat_container, dialogue_splitter

from . import iobase
from .. import mud_context, vfs, lang
from .styleaware_wrapper import tag_split_re
from .. import __version__ as tale_version_str
from ..driver import Driver
from ..player import PlayerConnection

__all__ = ["HttpIo", "TaleWsgiApp", "TaleWsgiAppBase", "WsgiStartResponseType", "TaleFastAPIApp"]

WsgiStartResponseType = Callable[..., None]

# Try to import FastAPI-related dependencies
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
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


def squash_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Makes a cgi-parsed parameter dictionary into a dict where the values that
    are just a list of a single value, are converted to just that single value.
    """
    for key, value in parameters.items():
        if isinstance(value, (list, tuple)) and len(value) == 1:
            parameters[key] = value[0]
    return parameters


class HttpIo(iobase.IoAdapterBase):
    """
    I/O adapter for a http/browser based interface.
    This doubles as a wsgi app and runs as a web server using wsgiref or FastAPI.
    This way it is a simple call for the driver, it starts everything that is needed.
    """
    def __init__(self, player_connection: PlayerConnection, server: Any) -> None:
        super().__init__(player_connection)
        self.wsgi_server = server  # Can be WSGI or FastAPI server
        self.fastapi_mode = False  # Will be set to True if using FastAPI
        self.fastapi_server = None  # Reference to FastAPI app instance
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
        """mainloop for the web browser interface for single player mode"""
        import webbrowser
        from threading import Thread
        
        if self.fastapi_mode:
            # FastAPI mode
            protocol = "https" if self.fastapi_server.use_ssl else "http"
            hostname = player_connection.driver.story.config.mud_host
            port = player_connection.driver.story.config.mud_port
            if hostname.startswith("127.0"):
                hostname = "localhost"
            url = "%s://%s:%d/tale/" % (protocol, hostname, port)
            print("Access the game on this web server url (FastAPI/WebSocket):  ", url, end="\n\n")
            
            t = Thread(target=webbrowser.open, args=(url, ))
            t.daemon = True
            t.start()
            
            # Run FastAPI server in the main thread
            try:
                self.fastapi_server.run(player_connection.driver.story.config.mud_host, 
                                      player_connection.driver.story.config.mud_port)
            except KeyboardInterrupt:
                print("* break - stopping server loop")
                if lang.yesno(input("Are you sure you want to exit the Tale driver, and kill the game? ")):
                    pass
            print("Game shutting down.")
        else:
            # WSGI mode (original implementation)
            protocol = "https" if self.wsgi_server.use_ssl else "http"

            if self.wsgi_server.address_family == socket.AF_INET6:
                hostname, port, _, _ = self.wsgi_server.server_address
                if hostname[0] != '[':
                    hostname = '[' + hostname + ']'
                url = "%s://%s:%d/tale/" % (protocol, hostname, port)
                print("Access the game on this web server url (ipv6):  ", url, end="\n\n")
            else:
                hostname, port = self.wsgi_server.server_address
                if hostname.startswith("127.0"):
                    hostname = "localhost"
                url = "%s://%s:%d/tale/" % (protocol, hostname, port)
                print("Access the game on this web server url (ipv4):  ", url, end="\n\n")
            t = Thread(target=webbrowser.open, args=(url, ))        # type: ignore
        t.daemon = True
        t.start()
        while not self.stop_main_loop:
            try:
                self.wsgi_server.handle_request()
            except KeyboardInterrupt:
                print("* break - stopping server loop")
                if lang.yesno(input("Are you sure you want to exit the Tale driver, and kill the game? ")):
                    break
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


class TaleWsgiAppBase:
    """
    Generic wsgi functionality that is not tied to a particular
    single or multiplayer web server.
    """
    def __init__(self, driver: Driver) -> None:
        self.driver = driver

    def __call__(self, environ: Dict[str, Any], start_response: WsgiStartResponseType) -> Iterable[bytes]:
        method = environ.get("REQUEST_METHOD")
        path = environ.get('PATH_INFO', '').lstrip('/')
        if not path:
            return self.wsgi_redirect(start_response, "/tale/")
        if path.startswith("tale/"):
            if method in ("GET", "POST"):
                if method == "POST":
                    clength = int(environ['CONTENT_LENGTH'])
                    if clength > 1e6:
                        raise ValueError('Maximum content length exceeded')
                    inputstream = environ['wsgi.input']
                    qs = inputstream.read(clength).decode("utf-8")
                elif method == "GET":
                    qs = environ.get("QUERY_STRING", "")
                parameters = squash_parameters(parse_qs(qs, encoding="UTF-8"))
                return self.wsgi_route(environ, path[5:], parameters, start_response)
            else:
                return self.wsgi_invalid_request(start_response)
        return self.wsgi_not_found(start_response)

    def wsgi_route(self, environ: Dict[str, Any], path: str, parameters: Dict[str, str],
                   start_response: WsgiStartResponseType) -> Iterable[bytes]:
        if not path or path == "start":
            return self.wsgi_handle_start(environ, parameters, start_response)
        elif path == "about":
            return self.wsgi_handle_about(environ, parameters, start_response)
        elif path == "story":
            return self.wsgi_handle_story(environ, parameters, start_response)
        elif path == "tabcomplete":
            return self.wsgi_handle_tabcomplete(environ, parameters, start_response)
        elif path == "input":
            return self.wsgi_handle_input(environ, parameters, start_response)
        elif path == "eventsource":
            return self.wsgi_handle_eventsource(environ, parameters, start_response)
        elif path.startswith("static/"):
            return self.wsgi_handle_static(environ, path, start_response)
        elif path == "quit":
            return self.wsgi_handle_quit(environ, parameters, start_response)
        return self.wsgi_not_found(start_response)

    def wsgi_invalid_request(self, start_response: WsgiStartResponseType) -> Iterable[bytes]:
        """Called if invalid http method."""
        start_response('405 Method Not Allowed', [('Content-Type', 'text/plain')])
        return [b'Error 405: Method Not Allowed']

    def wsgi_not_found(self, start_response: WsgiStartResponseType) -> Iterable[bytes]:
        """Called if Url not found."""
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return [b'Error 404: Not Found']

    def wsgi_redirect(self, start_response: Callable, target: str) -> Iterable[bytes]:
        """Called to do a redirect"""
        start_response('302 Found', [('Location', target)])
        return []

    def wsgi_redirect_other(self, start_response: Callable, target: str) -> Iterable[bytes]:
        """Called to do a redirect see-other"""
        start_response('303 See Other', [('Location', target)])
        return []

    def wsgi_not_modified(self, start_response: WsgiStartResponseType) -> Iterable[bytes]:
        """Called to signal that a resource wasn't modified"""
        start_response('304 Not Modified', [])
        return []

    def wsgi_internal_server_error(self, start_response: Callable, message: str="") -> Iterable[bytes]:
        """Called when an internal server error occurred"""
        start_response('500 Internal server error', [])
        return [message.encode("utf-8")]

    def wsgi_internal_server_error_json(self, start_response: Callable, message: str="") -> Iterable[bytes]:
        """Called when an internal server error occurred, returns json response rather than html"""
        start_response('500 Internal server error', [('Content-Type', 'application/json; charset=utf-8')])
        message = '{"error": "%s"}' % message
        return [message.encode("utf-8")]

    def wsgi_handle_about(self, environ: Dict[str, Any], parameters: Dict[str, str],
                          start_response: WsgiStartResponseType) -> Iterable[bytes]:
        raise NotImplementedError("implement this in subclass")   # about page

    def wsgi_handle_quit(self, environ: Dict[str, Any], parameters: Dict[str, str],
                         start_response: WsgiStartResponseType) -> Iterable[bytes]:
        raise NotImplementedError("implement this in subclass")   # quit/logged out page

    def wsgi_handle_start(self, environ: Dict[str, Any], parameters: Dict[str, str],
                          start_response: WsgiStartResponseType) -> Iterable[bytes]:
        # start page / titlepage
        headers = [('Content-Type', 'text/html; charset=utf-8')]
        resource = vfs.internal_resources["web/index.html"]
        etag = self.etag(id(self), time.mktime(self.driver.server_started.timetuple()), resource.mtime, "start")
        if_none = environ.get('HTTP_IF_NONE_MATCH')
        if if_none and (if_none == '*' or etag in if_none):
            return self.wsgi_not_modified(start_response)
        headers.append(("ETag", etag))
        start_response("200 OK", headers)
        txt = resource.text.format(story_version=self.driver.story.config.version,
                                   story_name=self.driver.story.config.name,
                                   story_author=self.driver.story.config.author,
                                   story_author_email=self.driver.story.config.author_address)
        return [txt.encode("utf-8")]

    def wsgi_handle_story(self, environ: Dict[str, Any], parameters: Dict[str, str],
                          start_response: WsgiStartResponseType) -> Iterable[bytes]:
        headers = [('Content-Type', 'text/html; charset=utf-8')]
        resource = vfs.internal_resources["web/story.html"]
        etag = self.etag(id(self), time.mktime(self.driver.server_started.timetuple()), resource.mtime, "story")
        if_none = environ.get('HTTP_IF_NONE_MATCH')
        if if_none and (if_none == '*' or etag in if_none):
            return self.wsgi_not_modified(start_response)
        headers.append(("ETag", etag))
        start_response('200 OK', headers)

        txt = resource.text.format(story_version=self.driver.story.config.version,
                                   story_name=self.driver.story.config.name,
                                   story_author=self.driver.story.config.author,
                                   story_author_email=self.driver.story.config.author_address)
        txt = self.modify_web_page(environ["wsgi.session"]["player_connection"], txt)
        return [txt.encode("utf-8")]

    def wsgi_handle_eventsource(self, environ: Dict[str, Any], parameters: Dict[str, str],
                                start_response: WsgiStartResponseType) -> Iterable[bytes]:
        session = environ["wsgi.session"]
        conn = session.get("player_connection")
        if not conn:
            return self.wsgi_internal_server_error_json(start_response, "not logged in")
        start_response('200 OK', [('Content-Type', 'text/event-stream; charset=utf-8'),
                                  ('Cache-Control', 'no-cache'),
                                  # ('Transfer-Encoding', 'chunked'),    not allowed by wsgi
                                  ('X-Accel-Buffering', 'no')   # nginx
                                  ])
        yield (":" + ' ' * 2050 + "\n\n").encode("utf-8")   # padding for older browsers
        while self.driver.is_running():
            if conn.io and conn.player:
                conn.io.wait_html_available(timeout=15)   # keepalives every 15 sec
            if not conn.io or not conn.player:
                break
            html = conn.io.get_html_to_browser()
            special = conn.io.get_html_special()
            data = conn.io.get_data_to_browser()
            if html or special:
                location = conn.player.location # type : Optional[Location]
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
                    "text": "\n".join(html),
                    "special": special,
                    "turns": conn.player.turns,
                    "location": location.title if location else "???",
                    "location_image": location.avatar if location and location.avatar else "",
                    "npcs": npc_names if location else '',
                    "items": items if location else '',
                    "exits": exits if location else '',
                }
                result = "event: text\nid: {event_id}\ndata: {data}"\
                    .format(event_id=str(time.time()), data=json.dumps(response))
                yield (result + "\n\n"+ ' ' * 150 + "\n\n").encode("utf-8")
            elif data:
                for d in data:
                    result = "event: data\nid: {event_id}\ndata: {data}\n\n"\
                        .format(event_id=str(time.time()), data=d)
                    yield result.encode("utf-8")
            else:
                yield "data: keepalive\n\n".encode("utf-8")

    def wsgi_handle_tabcomplete(self, environ: Dict[str, Any], parameters: Dict[str, str],
                                start_response: WsgiStartResponseType) -> Iterable[bytes]:
        session = environ["wsgi.session"]
        conn = session.get("player_connection")
        if not conn:
            return self.wsgi_internal_server_error_json(start_response, "not logged in")
        start_response('200 OK', [('Content-Type', 'application/json; charset=utf-8'),
                                  ('Cache-Control', 'no-cache, no-store, must-revalidate'),
                                  ('Pragma', 'no-cache'),
                                  ('Expires', '0')])
        return [json.dumps(conn.io.tab_complete(parameters["prefix"], self.driver)).encode("utf-8")]

    def wsgi_handle_input(self, environ: Dict[str, Any], parameters: Dict[str, str],
                          start_response: WsgiStartResponseType) -> Iterable[bytes]:
        session = environ["wsgi.session"]
        conn = session.get("player_connection")
        if not conn:
            return self.wsgi_internal_server_error_json(start_response, "not logged in")
        cmd = parameters.get("cmd", "")
        if cmd and "autocomplete" in parameters:
            suggestions = conn.io.tab_complete(cmd, self.driver)
            if suggestions:
                conn.io.append_html_to_browser("<br><p><em>Suggestions:</em></p>")
                conn.io.append_html_to_browser("<p class='txt-monospaced'>" + " &nbsp; ".join(suggestions) + "</p>")
            else:
                conn.io.append_html_to_browser("<p>No matching commands.</p>")
        else:
            cmd = html_escape(cmd, False)
            if cmd:
                if conn.io.dont_echo_next_cmd:
                    conn.io.dont_echo_next_cmd = False
                elif conn.io.echo_input:
                    conn.io.append_html_to_browser("<span class='txt-userinput'>%s</span>" % cmd)
            conn.player.store_input_line(cmd)
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return []

    def wsgi_handle_license(self, environ: Dict[str, Any], parameters: Dict[str, str],
                            start_response: WsgiStartResponseType) -> Iterable[bytes]:
        license = "The author hasn't provided any license information."
        if self.driver.story.config.license_file:
            license = self.driver.resources[self.driver.story.config.license_file].text
        resource = vfs.internal_resources["web/about_license.html"]
        headers = [('Content-Type', 'text/html; charset=utf-8')]
        etag = self.etag(id(self), time.mktime(self.driver.server_started.timetuple()), resource.mtime, "license")
        if_none = environ.get('HTTP_IF_NONE_MATCH')
        if if_none and (if_none == '*' or etag in if_none):
            return self.wsgi_not_modified(start_response)
        headers.append(("ETag", etag))
        start_response("200 OK", headers)
        txt = resource.text.format(license=license,
                                   story_version=self.driver.story.config.version,
                                   story_name=self.driver.story.config.name,
                                   story_author=self.driver.story.config.author,
                                   story_author_email=self.driver.story.config.author_address)
        return [txt.encode("utf-8")]

    def wsgi_handle_static(self, environ: Dict[str, Any], path: str, start_response: WsgiStartResponseType) -> Iterable[bytes]:
        path = path[len("static/"):]
        if not self.wsgi_is_asset_allowed(path):
            return self.wsgi_not_found(start_response)
        try:
            return self.wsgi_serve_static("web/" + path, environ, start_response)
        except IOError:
            return self.wsgi_not_found(start_response)

    def wsgi_is_asset_allowed(self, path: str) -> bool:
        return path.endswith(".html") or path.endswith(".js") or path.endswith(".jpg") \
            or path.endswith(".png") or path.endswith(".gif") or path.endswith(".css") or path.endswith(".ico")

    def etag(self, *components: Any) -> str:
        return '"' + md5("-".join(str(c) for c in components).encode("ascii")).hexdigest() + '"'

    def wsgi_serve_static(self, path: str, environ: Dict[str, Any], start_response: WsgiStartResponseType) -> Iterable[bytes]:
        headers = []
        resource = vfs.internal_resources[path]
        if resource.mtime:
            mtime_formatted = formatdate(resource.mtime)
            etag = self.etag(id(vfs.internal_resources), resource.mtime, path)
            if_modified = environ.get('HTTP_IF_MODIFIED_SINCE')
            if if_modified:
                if parsedate(if_modified) >= parsedate(mtime_formatted):        # type: ignore
                    # the resource wasn't modified since last requested
                    return self.wsgi_not_modified(start_response)
            if_none = environ.get('HTTP_IF_NONE_MATCH')
            if if_none and (if_none == '*' or etag in if_none):
                return self.wsgi_not_modified(start_response)
            headers.append(("ETag", etag))
            headers.append(("Last-Modified", formatdate(resource.mtime)))
        if resource.is_text:
            # text
            headers.append(('Content-Type', resource.mimetype + "; charset=utf-8"))
            data = resource.text.encode("utf-8")
        else:
            # binary
            headers.append(('Content-Type', resource.mimetype))
            data = resource.data
        start_response('200 OK', headers)
        return [data]
    
    def modify_web_page(self, player_connection: PlayerConnection, html_content: str) -> None:
        """Modify the html before it is sent to the browser."""
        if not "wizard" in player_connection.player.privileges:
            html_content = html_content.replace('<label for="fileInput">Load character:</label>', '')
            html_content = html_content.replace('<input type="file" id="loadCharacterInput" accept=".json, .png, .jpeg, .jpg">', '')
        return html_content



class TaleWsgiApp(TaleWsgiAppBase):
    """
    The actual wsgi app that the player's browser connects to.
    Note that it is deliberatly simplistic and ony able to handle a single
    player connection; it only works for 'if' single-player game mode.
    """
    def __init__(self, driver: Driver, player_connection: PlayerConnection,
                 use_ssl: bool, ssl_certs: Tuple[str, str, str]) -> None:
        super().__init__(driver)
        self.completer = None
        self.player_connection = player_connection   # just a single player here
        CustomWsgiServer.use_ssl = use_ssl
        if use_ssl and ssl_certs:
            CustomWsgiServer.ssl_cert_locations = ssl_certs

    @classmethod
    def create_app_server(cls, driver: Driver, player_connection: PlayerConnection, *,
                          use_ssl: bool=False, ssl_certs: Tuple[str, str, str]=None) -> Callable:
        wsgi_app = SessionMiddleware(cls(driver, player_connection, use_ssl, ssl_certs))        # type: ignore
        wsgi_server = make_server(driver.story.config.mud_host, driver.story.config.mud_port, app=wsgi_app,
                                  handler_class=CustomRequestHandler, server_class=CustomWsgiServer)
        wsgi_server.timeout = 0.5
        return wsgi_server

    def wsgi_handle_quit(self, environ: Dict[str, Any], parameters: Dict[str, str],
                         start_response: WsgiStartResponseType) -> Iterable[bytes]:
        # Quit/logged out page. For single player, simply close down the whole driver.
        start_response('200 OK', [('Content-Type', 'text/html')])
        self.driver._stop_driver()
        return [b"<html><body><script>window.close();</script><p><strong>Tale game session ended.</strong></p>"
                b"<p>You may close this window/tab.</p></body></html>"]

    def wsgi_handle_about(self, environ: Dict[str, Any], parameters: Dict[str, str],
                          start_response: WsgiStartResponseType) -> Iterable[bytes]:
        # about page
        if "license" in parameters:
            return self.wsgi_handle_license(environ, parameters, start_response)
        start_response("200 OK", [('Content-Type', 'text/html; charset=utf-8')])
        resource = vfs.internal_resources["web/about.html"]
        txt = resource.text.format(tale_version=tale_version_str,
                                   story_version=self.driver.story.config.version,
                                   story_name=self.driver.story.config.name,
                                   uptime="%d:%02d:%02d" % self.driver.uptime,
                                   starttime=self.driver.server_started)
        return [txt.encode("utf-8")]


class CustomRequestHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args: Any):
        pass


class CustomWsgiServer(ThreadingMixIn, WSGIServer):
    """
    A simple wsgi server with a modest request queue size, meant for single user access.
    Set use_ssl to True to enable HTTPS mode instead of unencrypted HTTP.
    """
    request_queue_size = 10
    use_ssl = False
    ssl_cert_locations = ("./certs/localhost_cert.pem", "./certs/localhost_key.pem", "")    # certfile, keyfile, certpassword

    def __init__(self, server_address, rh_class):
        self.address_family = socket.AF_INET
        if server_address[0][0] == '[' and server_address[0][-1] == ']':
            self.address_family = socket.AF_INET6
            server_address = (server_address[0][1:-1], server_address[1], 0, 0)
        super().__init__(server_address, rh_class)

    def server_bind(self):
        if self.use_ssl:
            print("\n\nUsing SSL\n\n")
            import ssl
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.load_cert_chain(self.ssl_cert_locations[0], self.ssl_cert_locations[1] or None, self.ssl_cert_locations[2] or None)
            self.socket = ctx.wrap_socket(self.socket, server_side=True)
        return super().server_bind()


class SessionMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ: Dict[str, Any], start_response: WsgiStartResponseType) -> None:
        environ["wsgi.session"] = {
            "id": None,
            "player_connection": self.app.player_connection
        }
        return self.app(environ, start_response)


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
                        # 1. Handle new player input (if any)
                        try:
                            data = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                            self._handle_player_input(player, data)
                        except asyncio.TimeoutError:
                            pass  # no input received
                        
                        # 2. Handle new server output
                        if player.io:
                            try:
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
                                elif data_items:
                                    for d in data_items:
                                        response = {"type": "data", "data": d}
                                        await websocket.send_text(json.dumps(response))
                                else:
                                    # No output available, wait briefly
                                    await asyncio.sleep(0.05)
                        else:
                            break
                            
                except WebSocketDisconnect:
                    self._cleanup_player(player)
                except Exception as e:
                    print(f"WebSocket error: {e}")
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
                    cmd = html_escape(cmd, False)
                    if cmd:
                        if conn.io.dont_echo_next_cmd:
                            conn.io.dont_echo_next_cmd = False
                        elif conn.io.echo_input:
                            conn.io.append_html_to_browser("<span class='txt-userinput'>%s</span>" % cmd)
                    conn.player.store_input_line(cmd)
            except json.JSONDecodeError:
                # Handle plain text input for backward compatibility
                cmd = html_escape(data, False)
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
