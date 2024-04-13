

from tale.llm.contexts.DungeonLocationsContext import DungeonLocationsContext
from tale.llm.contexts.EvokeContext import EvokeContext
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


