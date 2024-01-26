

from os import getcwd
from wsgiref.simple_server import WSGIServer
from tale.player import PlayerConnection
from tale.tio.if_browser_io import HttpIo, TaleWsgiApp
from tale.tio.mud_browser_io import TaleMudWsgiApp
from tests.supportstuff import FakeDriver


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

    def test_remove_load_character_button(self):
        connection = PlayerConnection()
        driver = FakeDriver()
        wsgi_app = TaleWsgiApp(driver=driver, player_connection=connection, use_ssl=False, ssl_certs=None)

        load_button = '<input type="file" id="loadCharacterInput" accept=".json, .png, .jpeg, .jpg">'
        with open('tale/web/story.html', 'r') as file:
            contents = file.read()
            assert load_button in contents
            result = wsgi_app.modify_web_page(connection, contents)
        
        assert load_button not in result

    def test_remove_save_button(self):
        connection = PlayerConnection()
        driver = FakeDriver()
        wsgi_app = TaleMudWsgiApp(driver=driver, use_ssl=False, ssl_certs=None)

        save_button = '<input type="button" id="saveButton" value="Save story" onclick="showSaveDialog()" readonly/>'
        with open('tale/web/story.html', 'r') as file:
            contents = file.read()
            assert save_button in contents
            result = wsgi_app.modify_web_page(connection, contents)
        
        assert save_button not in result
        

