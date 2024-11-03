import pytest
import responses
from tale import util
from tale.llm.llm_io import IoUtil
from tale.llm.llm_utils import LlmUtil
from tale.story_context import StoryContext
from tests.supportstuff import FakeDriver

class TestStoryContext:

    dummy_config = {
        'BACKEND': 'kobold_cpp',
        'USER_START': '',
        'USER_END': '',
        'DIALOGUE_PROMPT': '',
    }

    dummy_backend_config = {
        'URL': 'http://localhost:5001',
        'ENDPOINT': '/api/v1/generate',
        'STREAM': False,
        'STREAM_ENDPOINT': '',
        'DATA_ENDPOINT': '',
        'OPENAI_HEADERS': '',
        'OPENAI_API_KEY': '',
        'OPENAI_JSON_FORMAT': '',
        'API_PASSWORD': '',
    }

    def test_initialization(self):
        context = StoryContext(base_story="A hero's journey")
        assert context.base_story == "A hero's journey"
        assert context.current_section == ""
        assert context.past_sections == []

    def test_set_current_section(self):
        context = StoryContext(base_story="A hero's journey")
        context.set_current_section("Chapter 1")
        assert context.current_section == "Chapter 1"
        assert context.past_sections == []

        context.set_current_section("Chapter 2")
        assert context.current_section == "Chapter 2"
        assert context.past_sections == ["Chapter 1"]

    @responses.activate
    def test_increase_progress(self):
        context = StoryContext(base_story="A hero's journey")
        driver = FakeDriver()
        llm_util = LlmUtil(IoUtil(config=self.dummy_config, backend_config=self.dummy_backend_config)) # type: LlmUtil
        llm_util.backend = self.dummy_config['BACKEND']
        driver.llm_util = llm_util
        ctx = util.Context(driver=FakeDriver(), clock=None, config=None, player_connection=None)
        responses.add(responses.POST, self.dummy_backend_config['URL'] + self.dummy_backend_config['ENDPOINT'],
                  json={'results':[{'text':'progress'}]}, status=200)
        
        result = context.increase_progress(ctx)
        assert result == True
        assert context.progress == 1
        assert context.current_section == 'progress'
        assert context.past_sections == []
        context.increase_progress(ctx)
        assert context.progress == 2

        assert context.past_sections == ['progress']

        context.progress = 0.99999999999
        result = context.increase_progress(ctx)
        assert result == True
        assert context.progress > 1.0

        assert context.past_sections == ['progress', 'progress']

        context.progress = 9.9999999999999999999
        context.increase_progress(ctx)
        assert context.progress == 10.0

    def test_to_context(self):
        context = StoryContext(base_story="A hero's journey")
        context.set_current_section("Chapter 1")
        assert context.to_context() == "<story> Base plot: A hero's journey; Active section: Chapter 1</story>"

    def test_to_context_with_past(self):
        context = StoryContext(base_story="A hero's journey")
        context.set_current_section("Chapter 1")
        context.set_current_section("Chapter 2")
        assert context.to_context_with_past() == "<story> Base plot: A hero's journey; Past: Chapter 1; Active section:Chapter 2; Progress: 0.0/10.0;</story>"

    def test_from_json(self):
        data = {
            "base_story": "A hero's journey",
            "current_section": "Chapter 1",
            "past_sections": ["Prologue"],
            "progress": 0.5,
            "length": 10.0,
        }
        context = StoryContext().from_json(data)
        assert context.base_story == "A hero's journey"
        assert context.current_section == "Chapter 1"
        assert context.past_sections == ["Prologue"]
        assert context.progress == 0.5
        assert context.length == 10.0

    def test_to_json(self):
        context = StoryContext(base_story="A hero's journey")
        context.set_current_section("Prologue")
        context.set_current_section("Chapter 1")
        context.set_current_section("Chapter 2")
        data = context.to_json()
        assert data == {
            "base_story": "A hero's journey",
            "current_section": "Chapter 2",
            "past_sections": ["Prologue", "Chapter 1"],
            "progress": 0.0,
            "length": 10.0,
            "speed": 1.0
        }