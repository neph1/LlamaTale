"""
Tests for the scenario beat data model (tale/scenario.py) and for a story
with authored beats (stories/beats_test), advanced via StoryContext.set_beat
(the !set_beat wizard command).
"""
import json

import pytest

import tale.parse_utils as parse_utils
from tale.json_story import JsonStory
from tale.scenario import Beat, BeatStatus, load_beats
from tale.story_context import StoryContext
from tests.supportstuff import FakeDriver


class TestBeat:

    def test_status_str_is_lowercase(self):
        assert str(BeatStatus.LOCKED) == "locked"
        assert str(BeatStatus.ACTIVE) == "active"
        assert str(BeatStatus.COMPLETED) == "completed"
        assert str(BeatStatus.FAILED) == "failed"

    def test_defaults(self):
        beat = Beat("arrival")
        assert beat.id == "arrival"
        assert beat.description == ""
        assert beat.status == BeatStatus.LOCKED

    def test_to_json_from_json_round_trip(self):
        beat = Beat("arrival", "The investigators arrive.", BeatStatus.ACTIVE)
        restored = Beat.from_json(beat.to_json())
        assert restored.to_json() == {"id": "arrival", "description": "The investigators arrive.", "status": "active"}
        assert restored.status == BeatStatus.ACTIVE

    def test_from_json_defaults_to_locked(self):
        beat = Beat.from_json({"id": "one", "description": "First"})
        assert beat.status == BeatStatus.LOCKED


class TestLoadBeats:

    def test_load_beats(self):
        beats = load_beats([{"id": "a", "description": "A"}, {"id": "b", "description": "B", "status": "active"}])
        assert [beat.id for beat in beats] == ["a", "b"]
        assert beats[1].status == BeatStatus.ACTIVE

    def test_load_beats_allows_empty_description(self):
        beats = load_beats([{"id": "a", "description": ""}])
        assert beats[0].description == ""

    def test_load_beats_rejects_duplicate_ids(self):
        with pytest.raises(ValueError):
            load_beats([{"id": "a", "description": "A"}, {"id": "a", "description": "B"}])

    def test_load_beats_rejects_empty_id(self):
        with pytest.raises(ValueError):
            load_beats([{"id": "", "description": "A"}])

    def test_load_beats_requires_description_key(self):
        with pytest.raises(ValueError):
            load_beats([{"id": "a"}])


class TestBeatsStoryConfig:

    def test_story_config_beats_key_is_parsed(self):
        config = parse_utils.load_story_config(parse_utils.load_json('stories/beats_test/story_config.json'))
        assert [beat.id for beat in config.beats] == ["arrival", "suspicion", "descent"]
        assert all(isinstance(beat, Beat) for beat in config.beats)

    def test_story_config_beats_round_trip(self):
        config = parse_utils.load_story_config(parse_utils.load_json('stories/beats_test/story_config.json'))
        stored = parse_utils.save_story_config(config)
        assert [beat["id"] for beat in stored["beats"]] == ["arrival", "suspicion", "descent"]
        reloaded = parse_utils.load_story_config(stored)
        assert [beat.id for beat in reloaded.beats] == ["arrival", "suspicion", "descent"]

    def test_story_config_rejects_duplicate_beat_ids(self):
        config_json = parse_utils.load_json('stories/beats_test/story_config.json')
        config_json["beats"].append({"id": "arrival", "description": "duplicate"})
        with pytest.raises(ValueError):
            parse_utils.load_story_config(config_json)


class TestBeatsStory:
    """The test story with three authored beats: the beat pointer walks
    0 -> 2 via set_beat, to_context shows the active beat description,
    and a save contains the beat statuses."""

    def _load_story(self) -> JsonStory:
        driver = FakeDriver()
        story = JsonStory('stories/beats_test/', parse_utils.load_story_config(parse_utils.load_json('stories/beats_test/story_config.json')))
        story.init(driver)
        return story

    def test_authored_beats_loaded_on_init(self):
        story = self._load_story()
        context = story.config.context
        assert isinstance(context, StoryContext)
        assert context.authored == True
        assert [beat.id for beat in context.beats] == ["arrival", "suspicion", "descent"]
        assert [beat.status for beat in context.beats] == [BeatStatus.ACTIVE, BeatStatus.LOCKED, BeatStatus.LOCKED]
        assert "Active beat: The investigators arrive at the boarding house." in context.to_context()

    def test_pointer_walks_through_all_beats(self):
        story = self._load_story()
        context = story.config.context
        assert context.active_beat().id == "arrival"
        context.set_beat("suspicion")
        assert context.active_beat().id == "suspicion"
        assert context.beats[0].status == BeatStatus.COMPLETED
        context.set_beat("descent")
        assert context.active_beat().id == "descent"
        assert [beat.status for beat in context.beats] == [BeatStatus.COMPLETED, BeatStatus.COMPLETED, BeatStatus.ACTIVE]
        assert "Active beat: The cellar holds the answer." in context.to_context()
        assert "The investigators arrive at the boarding house." in context.to_context_with_past()
        # an unknown id leaves the state unchanged
        assert context.set_beat("nope") is None
        assert context.active_beat().id == "descent"

    def test_save_contains_beat_statuses(self, tmp_path):
        story = self._load_story()
        context = story.config.context
        context.set_beat("suspicion")
        assert context.active_beat().id == "suspicion"
        story.save(str(tmp_path), allow_absolute=True)
        saved = json.load(open(tmp_path / 'story_config.json'))
        assert [beat["id"] for beat in saved["context"]["beats"]] == ["arrival", "suspicion", "descent"]
        assert [beat["status"] for beat in saved["context"]["beats"]] == ["completed", "active", "locked"]
        assert [beat["id"] for beat in saved["beats"]] == ["arrival", "suspicion", "descent"]
        # and the saved story loads back with its runtime beat state
        reloaded = JsonStory(str(tmp_path) + '/', parse_utils.load_story_config(saved))
        assert [beat.status for beat in reloaded.config.context.beats] == [BeatStatus.COMPLETED, BeatStatus.ACTIVE, BeatStatus.LOCKED]

    def test_manager_save_load_round_trip(self, tmp_path):
        from tale.story_manager import StoryManager
        story = self._load_story()
        mgr = StoryManager(story)
        context = story.config.context
        context.set_beat("suspicion")
        assert context.active_beat().id == "suspicion"
        mgr.save(str(tmp_path))
        # advance further, then load the save again: runtime beat state is restored
        context.set_beat("descent")
        assert context.active_beat().id == "descent"
        mgr.load(str(tmp_path))
        context = mgr.story.config.context
        assert isinstance(context, StoryContext)
        assert context.authored == True
        assert [beat.status for beat in context.beats] == [BeatStatus.COMPLETED, BeatStatus.ACTIVE, BeatStatus.LOCKED]
        assert context.active_beat().id == "suspicion"
        state = mgr.get_story_state()
        assert [beat["id"] for beat in state["beats"]] == ["arrival", "suspicion", "descent"]
        assert state["current_section"] == "The landlady's story does not add up."
        assert state["past_sections"] == ["The investigators arrive at the boarding house."]
