

import json
from tale.base import Location
from tale.llm.contexts.BaseContext import BaseContext


class ActionContext(BaseContext):

    def __init__(self, story_context: str, story_type: str, character_name: str, character_card: str, event_history: str, location: Location, actions: list):
        super().__init__(story_context)
        self.story_type = story_type
        self.character_name = character_name
        self.character_card = character_card
        self.event_history = event_history.replace('<break>', '\n')
        self.location = location
        self.actions = actions


    def to_prompt_string(self) -> str:
        actions = ', '.join()
        characters = {}
        for living in self.location.livings:
            if living.visible and living.name != self.character_name.lower():
                if living.alive:
                    characters[living.name] = living.short_description
                else:
                    characters[living.name] = f"{living.short_description} (dead)"
        exits = self.location.exits.keys()
        items = [item.name for item in self.location.items if item.visible]
        return f"Story context:{self.story_context}; Story type:{self.story_type}; Available actions: {actions}; Location:{self.location.name}, {self.location.description}; Available exits: {exits}; Self: {self.character_card}; Present items: {items}; Present characters: {json.dumps(characters)}; History:{self.event_history};"