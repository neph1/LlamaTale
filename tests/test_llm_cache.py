import tale.llm.llm_cache as llm_cache

class TestLlmCache():
    """ Test LlmCache class"""

    def setup_method(self, test_method):
        llm_cache.event_cache = {}
        llm_cache.look_cache = {}
        llm_cache.tell_cache = {}

    def test_hash(self):
        """ Test hash function """
        hash_value = llm_cache.generate_hash("test")
        assert hash_value == hash("test")

    def test_get_non_existent_event(self):
        """ Test get_events function with non-existent event """
        assert llm_cache.get_events([1337]) == ""

    def test_cache_event(self):
        """ Test cache_event function """
        event_hash = llm_cache.cache_event("test")
        assert llm_cache.get_events([event_hash]) == "test"

        event_hash2 = hash("test2")
        llm_cache.cache_event("test2", event_hash2)
        assert llm_cache.get_events([event_hash2]) == "test2"

        assert llm_cache.get_events([event_hash, event_hash2]) == "test, test2"

    def test_cache_look(self):
        """ Test cache_look function """
        look_hash = llm_cache.cache_look("test")
        assert llm_cache.get_looks([look_hash]) == "test"

        look_hash2 = hash("test2")
        llm_cache.cache_look("test2", look_hash2)
        assert llm_cache.get_looks([look_hash2]) == "test2"

        assert llm_cache.get_looks([look_hash, look_hash2]) == "test, test2"


    def test_cache_tell(self):
        """ Test cache_tell function """
        tell_hash = llm_cache.cache_tell("test")
        assert llm_cache.get_tells([tell_hash]) == "test"

        tell_hash2 = hash("test2")
        llm_cache.cache_tell("test2", tell_hash2)
        assert llm_cache.get_tells([tell_hash2]) == "test2"

        assert llm_cache.get_tells([tell_hash, tell_hash2]) == "test, test2"



    