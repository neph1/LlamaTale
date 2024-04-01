

from typing import Generator
from tale.base import Location
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_utils import LlmUtil
from tale.player import PlayerConnection
from tale.story_builder import StoryBuilderBase


class DungeonStoryBuilder(StoryBuilderBase):

    def __init__(self, connection: PlayerConnection) -> None:
        self.story_info = StoryInfo()
        self.connection = connection
        
    def ask_story_type(self) -> Generator:
        self.story_info.type = yield "input", ("What genre would you like your story to be? Ie, 'A post apocalyptic scifi survival adventure', or 'Cozy social simulation with deep characters'")
        
    def ask_world_info(self) -> Generator:
        self.story_info.world_info = yield "input", ("Describe what the world is like. Use one to two paragraphs to outline the world and what it's like.")

    def ask_world_mood(self) -> Generator:
        self.story_info.world_mood = yield "input", ("How safe is the world? 5 is a happy place, -5 is nightmare mode.", self.validate_mood)

    def build(self) -> Generator:
        print("Building story")
        yield from self.ask_story_type()
        yield from self.ask_world_info()
        yield from self.ask_world_mood()

        if not self.story_info.name:
            self.story_info.name = "Dungeon Prompter"

        return self.story_info
    
    def apply_to_story(self, story: DynamicStory, llm_util: LlmUtil):
        story.config.name = self.story_info.name
        story.config.type = self.story_info.type
        story.config.world_info = self.story_info.world_info
        story.config.world_mood = self.story_info.world_mood
        self.connection.output("Generating story background...")
        story.config.context = llm_util.generate_story_background(world_info=story.config.world_info, 
                                                                            world_mood=story.config.world_mood,
                                                                            story_type=story.config.type)
        
        items = self.generate_world_items(llm_util, story.config.context, story.config.type, story.config.world_info, story.config.world_mood)
        for item in items:
            story._catalogue.add_item(item)
        
        creatures = self.generate_world_creatures(llm_util, story.config.context, story.config.type, story.config.world_info, story.config.world_mood)
        for creature in creatures:
            story._catalogue.add_creature(creature)

        zone = self.generate_starting_zone(llm_util, story.config.context, items, creatures)
        story.add_zone(zone)

        initial_start_location = Location(name="", descr=self.story_info.start_location)

        new_locations, exits, npcs = self.generate_start_location(llm_util, story, initial_start_location, zone)
        
        if len(npcs) > 0:
            self.add_start_quest(npcs, items)
            
        for npc in npcs:
            story.world.add_npc(npc)
            
        # fugly copy because a Location needs a name to init properly
        start_location = Location(name=initial_start_location.name, descr=self.story_info.start_location)
        start_location.init_inventory(list(initial_start_location.livings) + list(initial_start_location.items))

        zone.add_location(start_location)

        for location in new_locations:
            # try to add location, and if it fails, remove exit to it. but should it be possible to fail now?
            result = zone.add_location(location)
            if not result:
                for exit in exits:
                    if exit.name.capitalize() == location.name.capitalize():
                        exits.remove(exit)
        if len(exits) > 0:
            start_location.add_exits(exits)

        start_location_name = ".".join([zone.name, start_location.name.capitalize()])

        story.config.startlocation_player = start_location_name
        story.config.startlocation_wizard = start_location_name

        return start_location
    
class StoryInfo():
    def __init__(self) -> None:
        self.name = ""
        self.description = ""
        self.type = ""
        self.world_info = ""
        self.world_mood = 0
        self.start_location = ""