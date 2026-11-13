# This file contains the StoryBuilding class, which is responsible for generating the story background
from tale import parse_utils
from tale.llm import llm_config
from tale.llm.contexts.AdvanceStoryContext import AdvanceStoryContext
from tale.llm.dynamic_story import DynamicStory
from tale.llm.llm_io import IoUtil
from tale.story_context import StoryContext


class StoryBuilding():

    def __init__(self, io_util: IoUtil, default_body: dict, backend: str = 'kobold_cpp'):
        self.backend = backend
        self.io_util = io_util
        self.default_body = default_body

    def generate_story_background(self, world_mood: int, world_info: str, story_type: str) -> str:
        prompt = llm_config.params['STORY_BACKGROUND_PROMPT'].format(
            story_type=story_type,
            world_mood=parse_utils.mood_string_from_int(world_mood),
            world_info=world_info)
        request_body = self.default_body
        return self.io_util.synchronous_request(request_body, prompt=prompt)
    
    def advance_story_section(self, story_context: StoryContext) -> str:
        beat = story_context.advance_to_next_beat()
        if beat is not None:
            # authored beats: move the pointer to the next beat
            return beat.description
        if story_context.authored:
            # authored story exhausted: the last beat stays ACTIVE
            active = story_context.active_beat()
            return active.description if active else ""
        context = AdvanceStoryContext(story_context)
        prompt = llm_config.params['ADVANCE_STORY_PROMPT'].format(context=context.to_prompt_string())
        request_body = self.default_body
        result = self.io_util.synchronous_request(request_body, prompt=prompt)
        story_context.add_beat(result)
        return result
    