

from tale.llm.contexts.BaseContext import BaseContext


class DialogueContext(BaseContext):

    def __init__(self, 
            story_context: str,
            location_description: str,
            speaker_card: str,
            speaker_name: str,
            target_name: str,
            target_description: str):
        super().__init__(story_context)
        self.location_description = location_description
        self.speaker_card = speaker_card
        self.speaker_name = speaker_name
        self.target_name = target_name
        self.target_description = target_description


    def to_prompt_string(self) -> str:
        return f"Story context:{self.story_context}; Location:{self.location_description}; Self:{self.speaker_name}:{self.speaker_card}; Listener:{self.target_name}:{self.target_description};"