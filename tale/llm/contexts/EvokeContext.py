from tale.llm.contexts.BaseContext import BaseContext

class EvokeContext(BaseContext):

    def __init__(self, story_context: str, history: str, extra_context: str = '') -> None:
        super().__init__(story_context)
        self.history = history
        self.extra_context = extra_context

    def to_prompt_string(self) -> str:
        return f"Story context:{self.story_context}; History:{self.history}; " + f"{self.extra_context};" if self.extra_context else ''