

from tale.llm.contexts.BaseContext import BaseContext


class AdvanceStoryContext(BaseContext):
    
        def __init__(self, story_context: str):
            super().__init__(story_context)
    
        def to_prompt_string(self) -> str:
            return f"{self.story_context}"