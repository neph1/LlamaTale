

class BaseContext():

    def __init__(self, story_context: str) -> None:
        self.story_context = story_context

    def to_prompt_string(self) -> str:
        pass