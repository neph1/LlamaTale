
from tale.web import web_utils
from tale.web.web_utils import create_chat_container, copy_single_image, _check_file_exists


class TestWebUtils():


    def test_create_chat_container(self):
        result = create_chat_container("Bloated Murklin <:> Hello World!")

        assert "chat-container" in result
        assert '<div class="user-name" content="Bloated Murklin"></div>' in result
        assert '<div class="text-field" type="text">Hello World!</div>' in result

    def test_copy_single_image(self):
        web_utils.web_resources_path = "tale/web"
        copy_single_image("./tests/files", "test.jpg")
        assert _check_file_exists("test.jpg")