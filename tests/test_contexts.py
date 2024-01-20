

from tale.llm.contexts.EvokeContext import EvokeContext
from tale.llm.contexts.WorldGenerationContext import WorldGenerationContext


class TestPromptContexts():

    def test_evoke_context(self):
        context = EvokeContext(story_context='context', history='history')
        assert(context.to_prompt_string() == 'Story context:context; History:history; ')

    def test_world_generation_context(self):
        context = WorldGenerationContext(story_context='context', story_type='type', world_info='info', world_mood=1)
        assert(context.to_prompt_string() == 'Story context:context; Story type:type; World info:info; World mood: slightly friendly;')


