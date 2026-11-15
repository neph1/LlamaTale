"""
Tests for the scenario beat data model (tale/scenario.py), the typed story
events that satisfy beat goals, and for a story with authored beats
(stories/beats_test), advanced via StoryContext.set_beat (the !set_beat
wizard command) or automatically by world events.
"""
import json

import pytest

import tale
import tale.parse_utils as parse_utils
from tale import mud_context
from tale.base import ParseResult
from tale.json_story import JsonStory
from tale.llm.LivingNpc import LivingNpc
from tale.llm.dynamic_story import DynamicStory
from tale.llm.llm_utils import LlmUtil
from tale.quest import Quest, QuestType
from tale.scenario import (Beat, BeatStatus, Goal, Interacted, NpcKilled,
                           QuestCompleted, load_beats, publish_story_event)
from tale.story_context import StoryContext
from tests.supportstuff import FakeDriver, FakeIoUtil


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
        assert restored.to_json() == {"id": "arrival", "description": "The investigators arrive.", "status": "active",
                                      "match": "all", "goals": []}
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
        # an unknown id adds a new beat and selects it
        beat = context.set_beat("epilogue", "The investigators leave.")
        assert beat.id == "epilogue"
        assert context.active_beat().id == "epilogue"
        assert context.beats[2].status == BeatStatus.COMPLETED

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


class TestGoal:

    def test_defaults_and_key(self):
        goal = Goal("kill", "Giant Rat")
        assert goal.type == "kill"
        assert goal.target == "Giant Rat"
        assert goal.satisfied == False
        assert goal.key == "kill:giant rat"

    def test_unknown_type_rejected(self):
        with pytest.raises(ValueError):
            Goal("have_item", "brass key")  # lands in a later phase

    def test_empty_target_rejected(self):
        with pytest.raises(ValueError):
            Goal("kill", "")

    def test_to_json_from_json_round_trip(self):
        goal = Goal("quest_complete", "The Map", satisfied=True)
        restored = Goal.from_json(goal.to_json())
        assert restored.to_json() == {"type": "quest_complete", "target": "The Map", "satisfied": True}

    def test_from_json_requires_type_and_target(self):
        with pytest.raises(ValueError):
            Goal.from_json({"type": "kill"})
        with pytest.raises(ValueError):
            Goal.from_json({"target": "rat"})
        with pytest.raises(ValueError):
            Goal.from_json("kill rat")

    def test_matches_event(self):
        assert Goal("quest_complete", "the map").matches_event(QuestCompleted(quest="The Map"))
        assert not Goal("quest_complete", "other quest").matches_event(QuestCompleted(quest="The Map"))
        assert Goal("interact", "mrs. corbin").matches_event(Interacted(npc="mrs. corbin", npc_title="Mrs. Corbin"))
        assert Goal("interact", "Mrs. Corbin").matches_event(Interacted(npc="mrs. corbin", npc_title="Mrs. Corbin"))
        assert not Goal("interact", "maid").matches_event(Interacted(npc="mrs. corbin"))
        assert Goal("kill", "giant rat").matches_event(NpcKilled(npc="giant rat", npc_title="Giant Rat"))
        assert not Goal("kill", "giant rat").matches_event(Interacted(npc="giant rat"))
        assert not Goal("interact", "rat").matches_event(NpcKilled(npc="rat"))


class TestBeatGoals:

    def test_from_json_without_goals_is_backward_compatible(self):
        beat = Beat.from_json({"id": "a", "description": "A", "status": "active"})
        assert beat.goals == []
        assert beat.match == "all"
        assert beat.goals_match() == False

    def test_invalid_match_rejected(self):
        with pytest.raises(ValueError):
            Beat("a", "A", match="sometimes")

    def test_record_event_marks_matching_goals(self):
        beat = Beat("a", "A", goals=[Goal("kill", "rat"), Goal("interact", "maid")])
        assert beat.record_event(NpcKilled(npc="rat")) == False  # match "all": interact still open
        assert beat.goals[0].satisfied == True
        assert beat.goals[1].satisfied == False
        assert beat.record_event(Interacted(npc="maid")) == True

    def test_match_any(self):
        beat = Beat("a", "A", goals=[Goal("kill", "rat"), Goal("interact", "maid")], match="any")
        assert beat.record_event(Interacted(npc="maid")) == True
        assert beat.record_event(NpcKilled(npc="someone else")) == True  # already matched

    def test_empty_goals_never_match(self):
        beat = Beat("a", "A")
        assert beat.record_event(NpcKilled(npc="rat")) == False
        assert beat.goals_match() == False

    def test_to_json_includes_goals_and_satisfied(self):
        beat = Beat("a", "A", goals=[Goal("kill", "rat")])
        beat.record_event(NpcKilled(npc="rat"))
        data = beat.to_json()
        assert data["goals"] == [{"type": "kill", "target": "rat", "satisfied": True}]
        assert data["match"] == "all"
        restored = Beat.from_json(data)
        assert restored.goals[0].satisfied == True
        assert restored.goals_match() == True


class TestLoadBeatsGoals:

    def test_load_beats_with_goals(self):
        beats = load_beats([{"id": "a", "description": "A", "match": "any",
                             "goals": [{"type": "interact", "target": "Mrs. Corbin"}]}])
        assert [(goal.type, goal.target) for goal in beats[0].goals] == [("interact", "Mrs. Corbin")]
        assert beats[0].match == "any"

    def test_load_beats_rejects_unknown_goal_type(self):
        with pytest.raises(ValueError):
            load_beats([{"id": "a", "description": "A", "goals": [{"type": "have_item", "target": "key"}]}])

    def test_load_beats_rejects_non_list_goals(self):
        with pytest.raises(ValueError):
            load_beats([{"id": "a", "description": "A", "goals": "kill rat"}])

    def test_load_beats_rejects_goal_missing_target(self):
        with pytest.raises(ValueError):
            load_beats([{"id": "a", "description": "A", "goals": [{"type": "kill"}]}])


class TestBeatsStoryConfigGoals:

    def test_beats_test_story_config_parses_goals(self):
        config = parse_utils.load_story_config(parse_utils.load_json('stories/beats_test/story_config.json'))
        by_id = {beat.id: beat for beat in config.beats}
        assert by_id["arrival"].goals == []
        assert [(goal.type, goal.target) for goal in by_id["suspicion"].goals] == [("interact", "Mrs. Corbin")]
        assert [(goal.type, goal.target) for goal in by_id["descent"].goals] == [("kill", "the thing in the cellar")]


class TestStoryContextGoalEvents:

    def _context(self, beats) -> StoryContext:
        context = StoryContext(base_story="A guest has vanished from a boarding house.")
        context.set_beats(beats)
        return context

    def test_kill_event_completes_active_beat_and_advances(self):
        context = self._context([Beat("hunt", "Hunt the rat.", goals=[Goal("kill", "giant rat")]),
                                 Beat("after", "The end.")])
        completed = context.on_story_event(NpcKilled(npc="giant rat", npc_title="Giant Rat"))
        assert completed == ["hunt"]
        assert context.beats[0].status == BeatStatus.COMPLETED
        assert context.active_beat().id == "after"

    def test_non_matching_event_keeps_beat_active(self):
        context = self._context([Beat("hunt", "Hunt the rat.", goals=[Goal("kill", "giant rat")]),
                                 Beat("after", "The end.")])
        assert context.on_story_event(NpcKilled(npc="someone else")) == []
        assert context.active_beat().id == "hunt"

    def test_interact_then_quest_complete_chain(self):
        context = self._context([
            Beat("interview", "Talk to the landlady.", goals=[Goal("interact", "Mrs. Corbin")]),
            Beat("map", "Obtain the map.", goals=[Goal("quest_complete", "The Map")]),
            Beat("confrontation", "Enter the cellar.", goals=[Goal("kill", "the thing in the cellar")]),
            Beat("epilogue", "The end."),
        ])
        assert context.on_story_event(Interacted(npc="mrs. corbin", npc_title="Mrs. Corbin")) == ["interview"]
        assert context.active_beat().id == "map"
        assert context.on_story_event(QuestCompleted(quest="The Map", giver="elid_gald")) == ["map"]
        assert context.active_beat().id == "confrontation"
        assert context.on_story_event(NpcKilled(npc="the thing in the cellar")) == ["confrontation"]
        assert context.active_beat().id == "epilogue"

    def test_event_recorded_on_locked_beat_completes_it_on_activation(self):
        context = self._context([
            Beat("interview", "Talk to the landlady.", goals=[Goal("interact", "Mrs. Corbin")]),
            Beat("confrontation", "Kill the thing.", goals=[Goal("kill", "the thing in the cellar")]),
            Beat("epilogue", "The end."),
        ])
        # the NPC dies while its beat is still locked: no transition yet
        assert context.on_story_event(NpcKilled(npc="the thing in the cellar")) == []
        assert context.active_beat().id == "interview"
        # activating the beat re-checks its goals: already satisfied, completes immediately
        beat = context.set_beat("confrontation")
        assert beat.id == "epilogue"
        assert [b.status for b in context.beats] == [BeatStatus.COMPLETED, BeatStatus.COMPLETED, BeatStatus.ACTIVE]

    def test_cascade_over_multiple_satisfied_beats(self):
        context = self._context([
            Beat("one", "One.", goals=[Goal("kill", "rat")]),
            Beat("two", "Two.", goals=[Goal("kill", "rat")]),
            Beat("three", "Three."),
        ])
        assert context.on_story_event(NpcKilled(npc="rat")) == ["one", "two"]
        assert context.active_beat().id == "three"

    def test_match_any_beat_completes_on_first_event(self):
        context = self._context([Beat("a", "A.", goals=[Goal("kill", "rat"), Goal("interact", "maid")], match="any"),
                                 Beat("b", "B.")])
        assert context.on_story_event(Interacted(npc="maid")) == ["a"]
        assert context.active_beat().id == "b"

    def test_goal_less_beat_stays_active_for_manual_advance(self):
        context = self._context([Beat("one", "One."), Beat("two", "Two.")])
        assert context.on_story_event(NpcKilled(npc="rat")) == []
        assert context.active_beat().id == "one"
        assert context.set_beat("two").id == "two"
        assert context.active_beat().id == "two"

    def test_pubsub_delivery_via_subscribe_events(self):
        context = self._context([Beat("interview", "Talk.", goals=[Goal("interact", "Mrs. Corbin")]),
                                 Beat("after", "After.")])
        context.subscribe_events()
        try:
            publish_story_event(Interacted(npc="mrs. corbin", npc_title="Mrs. Corbin"))
            assert context.active_beat().id == "after"
        finally:
            context.unsubscribe_events()
        # after unsubscribe the context no longer reacts
        context2 = self._context([Beat("x", "X.", goals=[Goal("kill", "rat")])])
        publish_story_event(NpcKilled(npc="rat"))
        assert context2.active_beat().id == "x"
        assert context.active_beat().id == "after"

    def test_quest_complete_publishes_event(self):
        context = self._context([Beat("map", "Obtain the map.", goals=[Goal("quest_complete", "The Map")]),
                                 Beat("after", "After.")])
        context.subscribe_events()
        try:
            Quest(name="The Map", type=QuestType.GIVE, target="map", giver="elid_gald").complete()
            assert context.active_beat().id == "after"
        finally:
            context.unsubscribe_events()

    def test_do_on_death_publishes_kill_event(self):
        mud_context.driver = FakeDriver()
        context = self._context([Beat("hunt", "Hunt the rat.", goals=[Goal("kill", "giant rat")]),
                                 Beat("after", "After.")])
        context.subscribe_events()
        try:
            rat = LivingNpc("Giant Rat", "m", age=4)
            rat.do_on_death()
            assert not rat.alive
            assert context.active_beat().id == "after"
        finally:
            context.unsubscribe_events()

    def test_do_say_publishes_interact_event(self):
        # same setup as tests/test_quests.py (dialogue needs a canned LLM response)
        driver = FakeDriver()
        driver.story = DynamicStory()
        driver.llm_util = LlmUtil(FakeIoUtil(response='{"response": "ok", "give":"", "sentiment":"pleased"}'))
        mud_context.driver = driver
        mud_context.config = driver.story.config
        context = self._context([Beat("interview", "Talk to the NPC.", goals=[Goal("interact", "TestNpc")]),
                                 Beat("after", "After.")])
        context.subscribe_events()
        try:
            npc = LivingNpc("TestNpc", "m", age=20)
            speaker = LivingNpc("TestNpc2", "m", age=20)
            npc.notify_action(parsed=ParseResult(verb="say", unparsed="TestNpc: hello there"), actor=speaker)
            assert context.active_beat().id == "after"
        finally:
            context.unsubscribe_events()

    def test_save_load_preserves_goals_and_satisfaction(self):
        context = self._context([
            Beat("interview", "Talk.", goals=[Goal("interact", "Mrs. Corbin")]),
            Beat("confrontation", "Kill the thing.", goals=[Goal("kill", "the thing in the cellar")]),
            Beat("epilogue", "The end."),
        ])
        context.on_story_event(NpcKilled(npc="the thing in the cellar"))  # recorded on the locked beat
        restored = StoryContext().from_json(json.loads(json.dumps(context.to_json())))
        assert restored.beats[1].goals[0].satisfied == True
        assert restored.active_beat().id == "interview"
        # after a save/load the satisfied goal still completes the beat on activation
        beat = restored.set_beat("confrontation")
        assert beat.id == "epilogue"
        assert [b.status for b in restored.beats] == [BeatStatus.COMPLETED, BeatStatus.COMPLETED, BeatStatus.ACTIVE]

    def test_story_manager_forwards_events_to_context(self):
        from tale.story_manager import StoryManager
        driver = FakeDriver()
        story = JsonStory('stories/beats_test/', parse_utils.load_story_config(parse_utils.load_json('stories/beats_test/story_config.json')))
        story.init(driver)
        mgr = StoryManager(story)  # subscribes its beat-event listener to the story-events topic
        context = story.config.context
        assert context.active_beat().id == "arrival"
        # the interact goal of the locked "suspicion" beat is satisfied by this event
        publish_story_event(Interacted(npc="mrs. corbin", npc_title="Mrs. Corbin"))
        assert context.active_beat().id == "arrival"  # goal-less beat still advances manually
        context.set_beat("suspicion")
        # suspicion's goal was already satisfied: it completes immediately and descent activates
        assert context.beats[1].status == BeatStatus.COMPLETED
        assert context.active_beat().id == "descent"
