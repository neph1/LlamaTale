

from tale import parse_utils
from tale.llm.contexts.BaseContext import BaseContext


class WorldGenerationContext(BaseContext):

    def __init__(self, story_context: str, story_type: str, world_info: str, world_mood: int) -> None:
        super().__init__(story_context)
        self.story_type = story_type
        self.world_info = world_info
        self.world_mood = world_mood

    def to_prompt_string(self) -> str:
        return f"Story context:{self.story_context}; Story type:{self.story_type}; World info:{self.world_info}; World mood:{parse_utils.mood_string_from_int(self.world_mood)};"