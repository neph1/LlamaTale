


from tale.resources_utils import pad_text_for_avatar


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