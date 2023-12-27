

from wsgiref.simple_server import WSGIServer
from tale.player import PlayerConnection
from tale.tio.if_browser_io import HttpIo
from tale.web.web_utils import create_chat_container


class TestHttpIo:

    player_conn = PlayerConnection()
    wsgi_server=WSGIServer(server_address=('', 8000), RequestHandlerClass=None)

    def test_render_output_non_formatted(self):
        http_io = HttpIo(player_connection=self.player_conn, wsgi_server=self.wsgi_server)

        http_io.render_output([("Hello World!", False)])

        assert http_io.get_html_to_browser()[0] == "<pre>Hello World!</pre>\n"

    def test_render_output_formatted(self):
        http_io = HttpIo(player_connection=self.player_conn, wsgi_server=self.wsgi_server)

        http_io.render_output([("Hello World!", True)])

        assert http_io.get_html_to_browser()[0] == "<p>Hello World!</p>\n"


    def test_render_output_dialogue_token(self):
        http_io = HttpIo(player_connection=self.player_conn, wsgi_server=self.wsgi_server)

        http_io.render_output([("Bloated Murklin <:> Hello World!", True)])

        result = http_io.get_html_to_browser()[0]
        assert "chat-container" in result
        assert '<div class="user-name" content="Bloated Murklin"></div>' in result
        assert '<div class="text-field" type="text">Hello World!</div>' in result
        
    def test_create_chat_container(self):
        result = create_chat_container("Bloated Murklin <:> Hello World!")

        assert "chat-container" in result
        assert '<div class="user-name" content="Bloated Murklin"></div>' in result
        assert '<div class="text-field" type="text">Hello World!</div>' in result