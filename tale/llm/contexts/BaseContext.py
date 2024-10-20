from abc import ABC, abstractmethod
from typing import Union

from tale.story import StoryContext


class BaseContext(ABC):

    def __init__(self, story_context: Union[StoryContext, str]) -> None:
        if isinstance(story_context, StoryContext):
            self.story_context = story_context.to_context_with_past()
        else:
            self.story_context = story_context

    @abstractmethod
    def to_prompt_string(self) -> str:
        pass