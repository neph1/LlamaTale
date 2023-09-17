

from tale.player import PlayerConnection
from tale.story import StoryConfig


class StoryBuilder():

    def __init__(self, conn: PlayerConnection, config: StoryConfig) -> None:
        self.conn = conn
        self.config = config
        
    def ask_story_type(self):
        self.conn.output("What genre would you like your story to be? Ie, 'A post apocalyptic scifi survival adventure', or 'Cozy social simulation with deep characters'")
        
    def ask_world_info(self):
        self.conn.output("Describe what the world is like. Use one to two paragraphs to outline the world and what it's like.")

    def ask_world_mood(self):
        self.conn.output("How safe is the world? 5 is a happy place, -5 is nightmare mode.")

    def ask_start_location(self):
        self.conn.output("Where does the story start? Describe the starting location.")