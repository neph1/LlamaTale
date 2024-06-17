

from tale.base import Location
from tale.llm.contexts.ActionContext import ActionContext
from tale.llm.contexts.BaseContext import BaseContext


class FollowContext(ActionContext):

    def __init__(self, story_context: str, story_type: str, character_name: str, character_card: str, event_history: str, location: Location, asker_name: str, asker_card: str, asker_reason: str):
        super().__init__(story_context, story_type, character_name, character_card, event_history, location, [])
        self.asker_name = asker_name
        self.asker_card = asker_card
        self.asker_reason = asker_reason # Added last in actual prompt

    def to_prompt_string(self) -> str:
        return f"Story context:{self.story_context}; Story type:{self.story_type}; Location:{self.location.name}, {self.location.description}; Self({self.character_name}): {self.character_card}; Asker({self.asker_name}): {self.asker_card} ; History:{self.event_history};"