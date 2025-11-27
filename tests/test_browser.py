

from os import getcwd
from tale.player import PlayerConnection
from tale.tio.if_browser_io import HttpIo
from tests.supportstuff import FakeDriver


class TestHttpIo:

    player_conn = PlayerConnection()

    def test_render_output_non_formatted(self):
        http_io = HttpIo(player_connection=self.player_conn, server=None)

        http_io.render_output([("Hello World!", False)])

        assert http_io.get_html_to_browser()[0] == "<pre>Hello World!</pre>\n"

    def test_render_output_formatted(self):
        http_io = HttpIo(player_connection=self.player_conn, server=None)

        http_io.render_output([("Hello World!", True)])

        assert http_io.get_html_to_browser()[0] == "<p>Hello World!</p>\n"


    def test_render_output_dialogue_token(self):
        http_io = HttpIo(player_connection=self.player_conn, server=None)

        http_io.render_output([("Bloated Murklin <:> Hello World!", True)])

        result = http_io.get_html_to_browser()[0]
        assert "chat-container" in result
        assert '<div class="user-name" content="Bloated Murklin"></div>' in result
        assert '<div class="text-field" type="text">Hello World!</div>' in result

    def test_send_data(self):
        http_io = HttpIo(player_connection=self.player_conn, server=None)

        http_io.send_data('{"test": "test"}')

        assert http_io.get_data_to_browser()[0] == '{"test": "test"}'
        

