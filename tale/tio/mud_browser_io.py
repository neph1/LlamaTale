"""
Webbrowser based I/O for a multi player ('mud') server.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import hashlib
import http.cookies
import random
import sys
import time
import socket
from html import escape as html_escape
from socketserver import ThreadingMixIn
from typing import Dict, Iterable, Any, List, Tuple
from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler

from .. import vfs
from .if_browser_io import HttpIo, TaleWsgiAppBase, WsgiStartResponseType
from .. import __version__ as tale_version_str
from ..driver import Driver
from ..player import PlayerConnection

__all__ = ["MudHttpIo", "TaleMudWsgiApp"]


class MemorySessionFactory:
    def __init__(self):
        self.storage = {}

    def generate_id(self) -> str:
        string = "%d%d%f" % (random.randint(0, sys.maxsize), id(self), time.time())
        return hashlib.sha1(string.encode("ascii")).hexdigest()

    def load(self, sid: str) -> Any:
        sid = sid or self.generate_id()
        if sid not in self.storage:
            session = {
                "id": sid,
                "created": time.time()
            }
            self.storage[sid] = session
        return self.storage[sid]

    def save(self, session: Any) -> str:
        session["id"] = sid = session["id"] or self.generate_id()
        self.storage[sid] = session
        return sid

    def delete(self, sid: str) -> None:
        if sid in self.storage:
            del self.storage[sid]


class MudHttpIo(HttpIo):
    """
    I/O adapter for a http/browser based interface.
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


class TaleMudWsgiApp(TaleWsgiAppBase):
    """
    The actual wsgi app that the player's browser connects to.
    This one is capable of dealing with multiple connected clients (multi-player).
    """
    def __init__(self, driver: Driver, use_ssl: bool, ssl_certs: Tuple[str, str, str]) -> None:
        super().__init__(driver)
        CustomWsgiServer.use_ssl = use_ssl
        if use_ssl and ssl_certs:
            CustomWsgiServer.ssl_cert_locations = ssl_certs

    @classmethod
    def create_app_server(cls, driver: Driver, *,
                          use_ssl: bool=False, ssl_certs: Tuple[str, str, str]=None) -> WSGIServer:
        wsgi_app = SessionMiddleware(cls(driver, use_ssl, ssl_certs), MemorySessionFactory())    # type: ignore
        wsgi_server = make_server(driver.story.config.mud_host, driver.story.config.mud_port, app=wsgi_app,
                                  handler_class=CustomRequestHandler, server_class=CustomWsgiServer)
        return wsgi_server

    def wsgi_handle_story(self, environ: Dict[str, Any], parameters: Dict[str, str],
                          start_response: WsgiStartResponseType) -> Iterable[bytes]:
        session = environ["wsgi.session"]
        if "player_connection" not in session:
            # create a new connection
            conn = self.driver.connect_player("web", 0)
            session["player_connection"] = conn
        return super().wsgi_handle_story(environ, parameters, start_response)

    def wsgi_handle_eventsource(self, environ: Dict[str, Any], parameters: Dict[str, str],
                                start_response: WsgiStartResponseType) -> Iterable[bytes]:
        session = environ["wsgi.session"]
        conn = session.get("player_connection")
        if not conn:
            return self.wsgi_internal_server_error_json(start_response, "not logged in")
        if not conn or not conn.player or not conn.io:
            raise SessionMiddleware.CloseSession("{\"error\": \"no longer a valid connection\"}", "application/json")
        return super().wsgi_handle_eventsource(environ, parameters, start_response)

    def wsgi_handle_quit(self, environ: Dict[str, Any], parameters: Dict[str, str],
                         start_response: WsgiStartResponseType) -> Iterable[bytes]:
        # Quit/logged out page. For multi player, get rid of the player connection.
        session = environ["wsgi.session"]
        conn = session.get("player_connection")
        if not conn:
            return self.wsgi_internal_server_error_json(start_response, "not logged in")
        if conn.player:
            self.driver.disconnect_player(conn)
        raise SessionMiddleware.CloseSession("<html><body><script>window.close();</script>"
                                             "<p><strong>Tale game session ended.</strong></p>"
                                             "<p>You may close this window/tab.</p></body></html>")

    def wsgi_handle_about(self, environ: Dict[str, Any], parameters: Dict[str, str],
                          start_response: WsgiStartResponseType) -> Iterable[bytes]:
        # about page
        if "license" in parameters:
            return self.wsgi_handle_license(environ, parameters, start_response)
        start_response("200 OK", [('Content-Type', 'text/html; charset=utf-8')])
        resource = vfs.internal_resources["web/about_mud.html"]
        player_table = []
        for name, conn in self.driver.all_players.items():
            player_table.append(html_escape("Name:  %s   connection: %s" % (name, conn.io)))
        player_table.append("</pre>")
        player_table_txt = "\n".join(player_table)
        txt = resource.text.format(tale_version=tale_version_str,
                                   story_version=self.driver.story.config.version,
                                   story_name=self.driver.story.config.name,
                                   uptime="%d:%02d:%02d" % self.driver.uptime,
                                   starttime=self.driver.server_started,
                                   num_players=len(self.driver.all_players),
                                   player_table=player_table_txt)
        return [txt.encode("utf-8")]
    
    def modify_web_page(self, player_connection: PlayerConnection, html_content: str) -> None:
        html_content = super().modify_web_page(player_connection, html_content)
        html_content = html_content.replace('<input type="button" id="saveButton" value="Save story" onclick="showSaveDialog()" readonly/>', '')
        return html_content


class CustomRequestHandler(WSGIRequestHandler):
    """A wsgi request handler that doesn't spam the log."""
    def log_message(self, format: str, *args: Any):
        pass


class CustomWsgiServer(ThreadingMixIn, WSGIServer):
    """
    A multi-threaded wsgi server with a larger request queue size than the default.
    Set use_ssl to True to enable HTTPS mode instead of unencrypted HTTP.
    """
    request_queue_size = 200
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
    """Wsgi middleware that injects session cookie logic."""

    session_cookie_name = "tale_session_id"

    class CloseSession(Exception):
        """
        Raise this from your wsgi function to remove the current session.
        The exception message is returned as last goodbye text to the browser.
        """
        def __init__(self, message: str, content_type: str="text/html") -> None:
            super().__init__(message)
            self.content_type = content_type

    def __init__(self, app: TaleWsgiAppBase, factory: MemorySessionFactory) -> None:
        self.app = app
        self.factory = factory

    def __call__(self, environ: Dict[str, Any], start_response: WsgiStartResponseType) -> Iterable[bytes]:
        path = environ.get('PATH_INFO', '')
        if not path.startswith("/tale/"):
            # paths not under /tale/ won't get a session
            return self.app(environ, start_response)

        cookies = Cookies.from_env(environ)
        sid = ""
        session_is_new = True
        if self.session_cookie_name in cookies:
            sid = cookies[self.session_cookie_name].value
            session_is_new = False
        environ["wsgi.session"] = self.factory.load(sid)

        # If the server runs behind a reverse proxy, you can configure the proxy
        # to pass along the uri that it exposes (our internal uri can be different)
        # via the X-Forwarded-Uri header. If we find this header we use it to
        # replace the "/tale" uri base by the one from the header, to use as cookie path.
        forwarded_uri = environ.get("HTTP_X_FORWARDED_URI", "/tale/")
        cookie_path = "/" + forwarded_uri.split("/", 2)[1]

        def wrapped_start_response(status: str, response_headers: List[Tuple[str, str]], exc_info: Any=None) -> Any:
            sid = self.factory.save(environ["wsgi.session"])
            if session_is_new:
                # add the new session cookie to response
                cookies = Cookies()     # type: ignore
                cookies.add_cookie(self.session_cookie_name, sid, cookie_path)
                response_headers.extend(cookies.get_http_headers())
            return start_response(status, response_headers, exc_info)

        try:
            return self.app(environ, wrapped_start_response)
        except SessionMiddleware.CloseSession as x:
            self.factory.delete(sid)
            # clear the browser cookie
            cookies = Cookies()     # type: ignore
            cookies.delete_cookie(self.session_cookie_name, cookie_path)
            response_headers = [('Content-Type', x.content_type)]
            response_headers.extend(cookies.get_http_headers())
            start_response("200 OK", response_headers)
            return [str(x).encode("utf-8")]


class Cookies(http.cookies.SimpleCookie):
    @staticmethod
    def from_env(environ: Dict[str, Any]) -> 'Cookies':
        cookies = Cookies()     # type: ignore
        if 'HTTP_COOKIE' in environ:
            cookies.load(environ['HTTP_COOKIE'])
        return cookies

    def add_cookie(self, name: str, value: str, path: str) -> None:
        self[name] = value
        morsel = self[name]
        morsel["path"] = path
        morsel["httponly"] = "1"

    def delete_cookie(self, name: str, path: str="") -> None:
        self[name] = "deleted"
        morsel = self[name]
        if path:
            morsel["path"] = path
        morsel["httponly"] = "1"
        morsel["max-age"] = "0"
        morsel["expires"] = "Thu, 01 Jan 1970 00:00:00 GMT"   # for IE

    def get_http_headers(self):
        return [("Set-Cookie", morsel.OutputString()) for morsel in self.values()]
