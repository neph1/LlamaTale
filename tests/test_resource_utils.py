


import os
from tale.resources_utils import check_file_exists_in_resources, pad_text_for_avatar, unpad_text
import shutil


class TestResourceUtils:

    def test_pad_for_avatar(self):
        """Test padding for avatar."""
        text = "This is a test."
        npc_name = "Test NPC"
        expected = "Test NPC <:> This is a test."
        assert pad_text_for_avatar(text, npc_name) == expected

    def test_pad_for_avatar_empty(self):
        """Test padding for avatar with empty text."""
        text = ""
        npc_name = "Test NPC"
        expected = "Test NPC <:> "
        assert pad_text_for_avatar(text, npc_name) == expected

    def test_pad_for_avatar_empty_npc(self):
        """Test padding for avatar with empty NPC name."""
        text = "This is a test."
        npc_name = ""
        expected = "This is a test."
        assert pad_text_for_avatar(text, npc_name) == expected

    def test_unpad_text(self):
        test_text = "Test text"
        assert unpad_text(test_text) == test_text
        test_text2 = "Test <:> text"
        assert unpad_text(test_text2) == "Test : text"

    # def test_check_file_exists_in_resources(self):
    #     """Test checking file exists in resources."""
    #     shutil.copyfile("./tests/files/test.jpg", "./tale/web/resources/test.jpg")
    #     file_name = "test"
    #     file_exists = check_file_exists_in_resources(file_name) == file_name
    #     os.remove("./tale/web/resources/test.jpg")
    #     assert file_exists