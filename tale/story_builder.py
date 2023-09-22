

from typing import Generator
from tale import lang
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
        min = -5,
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

