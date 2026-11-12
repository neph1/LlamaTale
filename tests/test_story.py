import pytest
import responses
from tale import util
from tale.llm.llm_io import IoUtil
from tale.llm.llm_utils import LlmUtil
from tale.scenario import Beat, BeatStatus
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
        assert context.beats == []
        assert context.authored == False

    def test_set_beats_default_statuses(self):
        context = StoryContext(base_story="A hero's journey")
        context.set_beats([Beat("one", "First"), Beat("two", "Second"), Beat("three", "Third")])
        assert context.authored == True
        assert [beat.status for beat in context.beats] == [BeatStatus.ACTIVE, BeatStatus.LOCKED, BeatStatus.LOCKED]

    def test_set_beats_rejects_duplicate_ids(self):
        context = StoryContext(base_story="A hero's journey")
        with pytest.raises(ValueError):
            context.set_beats([Beat("one", "First"), Beat("one", "Again")])
        with pytest.raises(ValueError):
            context.set_beats([Beat("", "No id")])

    def test_advance_to_next_beat(self):
        context = StoryContext(base_story="A hero's journey")
        context.set_beats([Beat("one", "First"), Beat("two", "Second")])
        beat = context.advance_to_next_beat()
        assert beat.id == "two"
        assert beat.status == BeatStatus.ACTIVE
        assert context.beats[0].status == BeatStatus.COMPLETED
        assert context.advance_to_next_beat() is None
        assert context.active_beat().id == "two"

    def test_add_beat_generated_ids(self):
        context = StoryContext(base_story="A hero's journey")
        beat = context.add_beat("Chapter 1")
        assert beat.id == "beat-0"
        assert beat.status == BeatStatus.ACTIVE
        beat2 = context.add_beat("Chapter 2")
        assert beat2.id == "beat-1"
        assert context.beats[0].status == BeatStatus.COMPLETED
        assert context.active_beat().description == "Chapter 2"
        assert [b.description for b in context.completed_beats()] == ["Chapter 1"]

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
        assert context.active_beat().description == 'progress'
        assert context.active_beat().id == 'beat-0'
        assert context.completed_beats() == []
        context.increase_progress(ctx)
        assert context.progress == 2

        assert [b.description for b in context.completed_beats()] == ['progress']

        context.progress = 0.99999999999
        result = context.increase_progress(ctx)
        assert result == True
        assert context.progress > 1.0

        assert [b.description for b in context.completed_beats()] == ['progress', 'progress']

        context.progress = 9.9999999999999999999
        context.increase_progress(ctx)
        assert context.progress == 10.0

    def test_increase_progress_authored_beats(self):
        # 3 authored beats over length 10: each beat spans 10/3 progress
        context = StoryContext(base_story="A hero's journey")
        context.set_beats([Beat("one", "First"), Beat("two", "Second"), Beat("three", "Third")])
        ctx = util.Context(driver=FakeDriver(), clock=None, config=None, player_connection=None)

        assert context.active_beat().id == "one"
        crossed = [context.increase_progress(ctx) for _ in range(3)]
        assert crossed == [False, False, False]  # progress 1..3, still inside the first beat (span 10/3)
        assert context.active_beat().id == "one"
        assert context.increase_progress(ctx) == True   # progress 4 crosses 10/3
        assert context.active_beat().id == "two"
        assert context.beats[0].status == BeatStatus.COMPLETED
        for _ in range(2):
            context.increase_progress(ctx)  # progress 5, 6
        assert context.active_beat().id == "two"
        assert context.increase_progress(ctx) == True   # progress 7 crosses 20/3
        assert context.active_beat().id == "three"
        for _ in range(3):
            context.increase_progress(ctx)  # progress 8, 9, 10
        # exhaustion: at progress == length the last beat stays ACTIVE
        assert context.progress == 10.0
        assert context.active_beat().id == "three"
        assert context.active_beat().status == BeatStatus.ACTIVE
        assert [b.status for b in context.beats] == [BeatStatus.COMPLETED, BeatStatus.COMPLETED, BeatStatus.ACTIVE]

    def test_to_context(self):
        context = StoryContext(base_story="A hero's journey")
        context.add_beat("Chapter 1")
        assert context.to_context() == "<story> Base plot: A hero's journey; Active beat: Chapter 1</story>"

    def test_to_context_with_past(self):
        context = StoryContext(base_story="A hero's journey")
        context.add_beat("Chapter 1")
        context.add_beat("Chapter 2")
        assert context.to_context_with_past() == "<story> Base plot: A hero's journey; Past: Chapter 1; Active beat: Chapter 2; Progress: 0.0/10.0;</story>"

    def test_from_json(self):
        data = {
            "base_story": "A hero's journey",
            "beats": [
                {"id": "beat-0", "description": "Prologue", "status": "completed"},
                {"id": "beat-1", "description": "Chapter 1", "status": "active"},
            ],
            "progress": 0.5,
            "length": 10.0,
        }
        context = StoryContext().from_json(data)
        assert context.base_story == "A hero's journey"
        assert [beat.id for beat in context.beats] == ["beat-0", "beat-1"]
        assert context.beats[0].status == BeatStatus.COMPLETED
        assert context.beats[1].status == BeatStatus.ACTIVE
        assert context.active_beat().description == "Chapter 1"
        assert context.progress == 0.5
        assert context.length == 10.0

    def test_from_json_legacy_migration(self):
        # old saves have current_section/past_sections and no beats
        data = {
            "base_story": "A hero's journey",
            "current_section": "Chapter 1",
            "past_sections": ["Prologue"],
            "progress": 0.5,
            "length": 10.0,
        }
        context = StoryContext().from_json(data)
        assert [beat.id for beat in context.beats] == ["beat-0", "beat-1"]
        assert context.beats[0].description == "Prologue"
        assert context.beats[0].status == BeatStatus.COMPLETED
        assert context.beats[1].description == "Chapter 1"
        assert context.beats[1].status == BeatStatus.ACTIVE
        assert context.active_beat().description == "Chapter 1"
        assert [b.description for b in context.completed_beats()] == ["Prologue"]

    def test_to_json(self):
        context = StoryContext(base_story="A hero's journey")
        context.add_beat("Prologue")
        context.add_beat("Chapter 1")
        context.add_beat("Chapter 2")
        data = context.to_json()
        assert data == {
            "base_story": "A hero's journey",
            "beats": [
                {"id": "beat-0", "description": "Prologue", "status": "completed"},
                {"id": "beat-1", "description": "Chapter 1", "status": "completed"},
                {"id": "beat-2", "description": "Chapter 2", "status": "active"},
            ],
            "progress": 0.0,
            "length": 10.0,
            "speed": 1.0
        }

    def test_to_json_from_json_round_trip(self):
        context = StoryContext(base_story="A hero's journey")
        context.set_beats([Beat("one", "First"), Beat("two", "Second")])
        context.advance_to_next_beat()
        context.progress = 4.0
        restored = StoryContext().from_json(context.to_json())
        assert restored.to_json() == context.to_json()
        assert [beat.status for beat in restored.beats] == [BeatStatus.COMPLETED, BeatStatus.ACTIVE]
