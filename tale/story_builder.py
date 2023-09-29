

from typing import Generator
from tale import lang
from tale.base import Location
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_utils import LlmUtil
from tale.player import PlayerConnection
from tale.story import StoryConfig


class StoryInfo():
    def __init__(self) -> None:
        self.name = ""
        self.description = ""
        self.type = ""
        self.world_info = ""
        self.world_mood = 0
        self.start_location = ""

class StoryBuilder:

    def __init__(self) -> None:
        self.story_info = StoryInfo()
        
    def ask_story_type(self) -> Generator:
        self.story_info.type = yield "input", ("What genre would you like your story to be? Ie, 'A post apocalyptic scifi survival adventure', or 'Cozy social simulation with deep characters'")
        
    def ask_world_info(self) -> Generator:
        self.story_info.world_info = yield "input", ("Describe what the world is like. Use one to two paragraphs to outline the world and what it's like.")

    def ask_world_mood(self) -> Generator:
        self.story_info.world_mood = yield "input", ("How safe is the world? 5 is a happy place, -5 is nightmare mode.", self.validate_mood)

    def ask_start_location(self) -> Generator:
        self.story_info.start_location = yield "input", ("Where does the story start? Describe the starting area.")

    def ask_name(self) -> Generator:
        self.story_info.name = yield "input", ("Would you like to name the story?")

    def ask_confirm(self) -> Generator:
        okay = yield "input", ("Confirm the story and venture on?", lang.yesno)
        return okay

    def build(self) -> Generator:
        print("Building story")
        yield from self.ask_story_type()
        yield from self.ask_world_info()
        yield from self.ask_world_mood()
        yield from self.ask_start_location()
        yield from self.ask_name()

        if not self.story_info.name:
            self.story_info.name = "A Tale of Anything"

        return self.story_info
    
    def validate_mood(self, value: str) -> int:
        min = -5
        max = 5
        try:
            int_value = (int) (value)
            if min and int_value < min:
                raise ValueError("Only values greater than or equal to {} are allowed. Try again.".format(min))
            if max and int_value > max:
                raise ValueError("Only values less than or equal to {} are allowed. Try again.".format(max))
            return int(value)       
        except ValueError:
            raise ValueError("Not an integer! Try again.")
        

    def apply_to_story(self, story: DynamicStory, llm_util: LlmUtil):
        story.config.name = self.story_info.name
        story.config.type = self.story_info.type
        story.config.world_info = self.story_info.world_info
        story.config.world_mood = self.story_info.world_mood
        #generate bg story
        print("Generating story background...")
        story.config.context = llm_util.generate_story_background(world_info=story.config.world_info, 
                                                                            world_mood=story.config.world_mood)
        
        assert(story.config.context)

        # generate zone
        print("Generating starting zone...")
        zone = llm_util.generate_start_zone(location_desc=self.story_info.start_location, 
                                                    story_type=self.story_info.type, 
                                                    story_context=story.config.context, 
                                                    world_mood=self.story_info.world_mood, 
                                                    world_info=self.story_info.world_info)
        assert(zone)

        story.add_zone(zone)
        # generate location
        print("Generating starting location...")
        start_location = Location(name="", descr=self.story_info.start_location)
        new_locations, exits = llm_util.generate_start_location(location=start_location, 
                                                                story_type=self.story_info.type, 
                                                                story_context=story.config.context,
                                                                world_info=self.story_info.world_info,
                                                                zone_info=zone.get_info())
        
        assert(new_locations)
        # fugly copy because a Location needs a name to init properly
        start_location = Location(name=start_location.name, descr=self.story_info.start_location)
        zone.add_location(start_location)

        for location in new_locations:
            # try to add location, and if it fails, remove exit to it
            result = zone.add_location(location)
            if not result:
                for exit in exits:
                    if exit.name == location.name:
                        exits.remove(exit)
        if len(exits) > 0:
            start_location.add_exits(exits)
        
        story.config.startlocation_player = start_location.name
        story.config.startlocation_wizard = start_location.name

        return start_location
