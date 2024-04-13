
from tale.llm.contexts.BaseContext import BaseContext
from tale.llm.contexts.WorldGenerationContext import WorldGenerationContext


class DungeonLocationsContext(WorldGenerationContext):
    
    def __init__(self, story_context: str, story_type: str, world_info: str, world_mood: int, zone_info: dict, rooms: list, depth: int, max_depth: int) -> None:
        super().__init__(story_context, story_type, world_info, world_mood)
        self.zone = zone_info
        self.rooms = rooms
        self.depth = depth
        self.max_depth = max_depth

    def to_prompt_string(self) -> str:
        return f"{super().to_prompt_string()}; Zone: {self.zone}; Depth: {round(self.depth / self.max_depth, 2)}, Rooms:{', '.join(self.rooms)};"