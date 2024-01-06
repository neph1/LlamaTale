from tale.llm.contexts.BaseContext import BaseContext

class EvokeContext(BaseContext):

    def __init__(self, story_context: str, history: str) -> None:
        super().__init__(story_context)
        self.history = history

    def to_prompt_string(self) -> str:
        return f"Story context:{self.story_context}; History:{self.history};"