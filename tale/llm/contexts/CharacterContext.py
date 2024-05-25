

from tale.llm.contexts.WorldGenerationContext import WorldGenerationContext


class CharacterContext(WorldGenerationContext):
    def __init__(self, story_context: str, story_type: str, world_info: str, key_words: list = [], world_mood: int = 0):
        super().__init__(story_type=story_type, story_context=story_context, world_info=world_info, world_mood=world_mood)
        self.key_words = key_words

    def to_prompt_string(self) -> str:
        return super().to_prompt_string() + f"story_type: {self.story_type}, world_info: {self.world_info}"