

from abc import ABC, abstractmethod


class BaseContext(ABC):

    def __init__(self, story_context: str) -> None:
        self.story_context = story_context

    @abstractmethod
    def to_prompt_string(self) -> str:
        pass