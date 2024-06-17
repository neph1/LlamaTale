

from tale.base import Location
from tale.llm.contexts.ActionContext import ActionContext
from tale.llm.contexts.DungeonLocationsContext import DungeonLocationsContext
from tale.llm.contexts.EvokeContext import EvokeContext
from tale.llm.contexts.FollowContext import FollowContext
from tale.llm.contexts.WorldGenerationContext import WorldGenerationContext


class TestPromptContexts():

    def test_evoke_context(self):
        context = EvokeContext(story_context='context', history='history')
        assert(context.to_prompt_string() == 'Story context:context; History:history; ')

    def test_world_generation_context(self):
        context = WorldGenerationContext(story_context='context', story_type='type', world_info='info', world_mood=1)
        assert(context.to_prompt_string() == 'Story context:context; Story type:type; World info:info; World mood: slightly friendly;')

    def test_dungeon_locations_context(self):
        rooms=['''{
        "0": {
        "index": 0,
        "name": "Entrance to dungeon",
        "description": "A dark and ominous entrance to the dungeon, guarded by a fearsome dragon."
        },
        "1": {
        "index": 1,
        "name": "Hallway",
        "description": "A long and winding hallway, lined with ancient tapestries and mysterious artifacts."
        },
        "2": {
        "index": 2,
        "name": "Small room",
        "description": "A small and dimly lit room, filled with strange and exotic plants."
        },
        "3": {
        "index": 3,
        "name": "Hallway",
        "description": "A narrow and winding hallway, with flickering torches casting eerie shadows on the walls."
        }
        }''']

        zone_info = '{"name":"Test Zone"}'

        context = DungeonLocationsContext(story_context='context', story_type='type', world_info='info', world_mood=1, zone_info=zone_info, rooms=rooms, depth=2, max_depth=4)

        result = context.to_prompt_string()

        assert('Depth: 0.5' in result)
        assert('"name": "Small room"' in result)
        assert('Test Zone' in result)

    def test_action_context(self):
        character_name = "Test character"
        character_card = "{actions}"
        history = "[history]"
        location = Location("TestLocation")
        action_list = ["say", "take", "wear"]
        action_context = ActionContext(story_context="test_context",
                                       story_type="test type",
                                       character_name=character_name,
                                       character_card=character_card,
                                       event_history=history,
                                       location=location,
                                       actions=action_list)
        
        result = action_context.to_prompt_string()

        assert character_card in result
        assert character_name in result
        assert "say" in result


    def test_follow_context(self):
        story_context = "test_context"
        story_type = "test type"
        character_name = "Test character"
        character_card = "{actions}"
        history = "[history]"
        location = Location("TestLocation", descr="Test description")
        asker_name = "Asker"
        asker_card = "{actions}"
        asker_reason = "Asker reason"
        follow_context = FollowContext(story_context=story_context,
                                       story_type=story_type,
                                       character_name=character_name,
                                       character_card=character_card,
                                       event_history=history,
                                       location=location,
                                       asker_name=asker_name,
                                       asker_card=asker_card,
                                       asker_reason=asker_reason)
        
        result = follow_context.to_prompt_string()

        assert asker_name in result
        assert asker_card in result
        assert asker_reason not in result
        assert character_name in result
        assert character_card in result
        assert history in result
        assert location.name in result
        assert location.description in result
        assert story_context in result
        assert story_type in result