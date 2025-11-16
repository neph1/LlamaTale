import random
from tale.base import Location
from tale.llm.character_card import CharacterCard
from tale.llm.contexts.BaseContext import BaseContext


class ActionContext(BaseContext):

    def __init__(self, story_context: str, story_type: str, character_name: str, character_card: CharacterCard, event_history: str, location: Location, actions: list):
        super().__init__(story_context)
        self.story_type = story_type
        self.character_name = character_name
        self.character_card = character_card
        self.event_history = event_history.replace('<break>', '\n')
        self.location = location
        self.actions = actions


    def to_prompt_string(self) -> str:
        actions = ', '.join(self.actions)
        characters = []
        for living in self.location.livings:
            if living.visible and not living.hidden and living.name != self.character_name.lower():
                character = f"{living.name}: {living.short_description}"
                if not living.alive:
                    character = character + " (dead)"
                characters.append(character)
        exits = self.location.exits.keys()
        items = [item.name for item in self.location.items if item.visible]
        examples = []
        if len(items) > 0:
            examples.append(f'{{"goal":"", "thoughts":"I want this thing.", "action":"take", "target":{random.choice(items)}, "text":""}}')
        if len(exits) > 0:
            examples.append(f'{{"goal":"", "thoughts":"I want to go there.", "action":"move", "target":{random.choice(list(exits))}, "text":""}}')
        if len(characters) > 0:
            examples.append(f'{{"goal":"", "thoughts":"", "action":"say", "target":{random.choice(characters)}, "text":""}}')
        return f"Story context:{self.story_context}; Story type:{self.story_type}; Available actions: {actions}; Location: {self.location.name}, {self.location.description}; Available exits: {exits}; Self({self.character_name}): {self.character_card}; Present items: {items}; Present characters: {characters}; History:{self.event_history}; Example actions: {', '.join(examples)};"